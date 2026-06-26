"""
PostgreSQL CDC (Change Data Capture) via LISTEN/NOTIFY.

Two channels:
  issue_updated    — fires on INSERT/UPDATE to issues table
                     → embeds the changed row immediately (not on 5-min poll)
  issue_note_added — fires on INSERT to issue_updates table
                     → triggers escalation check in autonomous_agent

HNSW index is rebuilt after HNSW_REBUILD_THRESHOLD new embeddings accumulate
so search performance stays sub-5ms as data grows.
"""
import json
import os
import threading
import time
from observability.logging_utils import log_event

_HNSW_REBUILD_THRESHOLD = 50


def _embed_single_issue(issue_id: int) -> bool:
    """Embed one issue by id. Returns True if a new embedding was stored."""
    try:
        from sqlalchemy import text
        from core.db import SessionLocal
        from services.embedding_service import get_embedding

        with SessionLocal() as db:
            row = db.execute(
                text('SELECT id, title FROM issues WHERE id = :id'),
                {'id': issue_id}
            ).mappings().first()
            if not row:
                return False

            embedding = get_embedding(row['title'])
            if not embedding:
                return False

            emb_str = '[' + ','.join(str(x) for x in embedding) + ']'
            db.execute(
                text('UPDATE issues SET embedding = :e::vector WHERE id = :id'),
                {'e': emb_str, 'id': issue_id}
            )
            db.commit()
            log_event('cdc', {'action': 'embed_issue', 'issue_id': issue_id})
            return True
    except Exception as exc:
        log_event('cdc_error', {'action': 'embed_issue', 'issue_id': issue_id, 'error': str(exc)})
        return False


def _rebuild_hnsw() -> None:
    """Drop and recreate the HNSW index after enough new embeddings accumulate."""
    try:
        from sqlalchemy import text
        from core.db import SessionLocal
        with SessionLocal() as db:
            db.execute(text('DROP INDEX IF EXISTS issues_embedding_hnsw'))
            db.execute(text(
                'CREATE INDEX issues_embedding_hnsw '
                'ON issues USING hnsw (embedding vector_cosine_ops) '
                'WITH (m = 16, ef_construction = 64)'
            ))
            db.commit()
        log_event('cdc', {'action': 'hnsw_rebuild'})
    except Exception as exc:
        log_event('cdc_error', {'action': 'hnsw_rebuild', 'error': str(exc)})


def start_cdc_listener() -> None:
    """
    Start a daemon thread that holds a persistent PostgreSQL LISTEN connection.
    On notification: embeds the changed issue (issue_updated channel) or
    triggers escalation check (issue_note_added channel).
    Reconnects automatically after any connection error.
    """
    def _listener():
        import psycopg

        raw_dsn = os.getenv(
            'DATABASE_URL', 'postgresql://acme:acme@postgres:5432/acme_ops'
        ).replace('postgresql+psycopg://', 'postgresql://')

        new_embeddings = 0

        while True:
            try:
                with psycopg.connect(raw_dsn, autocommit=True) as conn:
                    conn.execute('LISTEN issue_updated')
                    conn.execute('LISTEN issue_note_added')
                    log_event('cdc', {'action': 'listener_started'})

                    # Stay connected indefinitely; notifies(timeout=30) returns on
                    # each notification OR after 30 s of silence — then we loop back.
                    while True:
                        for notify in conn.notifies(timeout=30.0):
                            try:
                                payload = json.loads(notify.payload)
                            except Exception:
                                continue

                            if notify.channel == 'issue_updated':
                                issue_id = payload.get('id')
                                if issue_id and _embed_single_issue(issue_id):
                                    new_embeddings += 1
                                    if new_embeddings >= _HNSW_REBUILD_THRESHOLD:
                                        _rebuild_hnsw()
                                        new_embeddings = 0

                            elif notify.channel == 'issue_note_added':
                                from services.autonomous_agent import check_issue_escalation
                                check_issue_escalation(payload.get('issue_id'))
                        # Timeout expired with no messages — loop back and wait again

            except Exception as exc:
                log_event('cdc_error', {'action': 'listener_reconnect', 'error': str(exc)})
                time.sleep(10)  # back off before reconnect

    t = threading.Thread(target=_listener, daemon=True, name='cdc-listener')
    t.start()
