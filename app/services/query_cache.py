"""
Two-layer query response cache.

Layer 1 — Redis exact cache
  Key: SHA-256(normalised_query + sorted_roles + customer_name)
  Value: JSON {answer, plan_summary}   TTL: 15 minutes
  Cost: O(1) Redis GET — ~1 ms

Layer 2 — pgvector semantic cache
  Embeds the query, finds cosine-similar cached queries > SIMILARITY_THRESHOLD.
  Catches paraphrases: "status of Nexus?" and "how is Nexus doing?" share a cache hit.
  Cost: 1 OpenAI embed call (~80 ms) + 1 pgvector ANN search (~5 ms)
  Only runs when OPENAI_API_KEY is configured; degrades gracefully otherwise.

Write operations (recommend, create action) are never cached.
"""
import hashlib
import json
import threading
from typing import Optional

from core.redis_client import r
from observability.logging_utils import log_event

_EXACT_TTL = 900          # 15 minutes
_SIMILARITY_THRESHOLD = 0.92
_WRITE_HINTS = {'recommend', 'create action', 'add action', 'suggest action', 'schedule'}


def _is_cacheable(query: str) -> bool:
    q = query.lower()
    return not any(hint in q for hint in _WRITE_HINTS)


def _exact_key(query: str, roles: list, customer: str) -> str:
    raw = f'{query.lower().strip()}|{",".join(sorted(roles))}|{customer.lower()}'
    return 'qcache:exact:' + hashlib.sha256(raw.encode()).hexdigest()[:32]


def _scope_tag(roles: list, customer: str) -> str:
    return f'{",".join(sorted(roles))}|{customer.lower()}'


# ── Layer 1: Redis exact cache ────────────────────────────────────────────────

def get_exact_cached(query: str, roles: list, customer: str) -> Optional[dict]:
    if not _is_cacheable(query):
        return None
    try:
        raw = r.get(_exact_key(query, roles, customer))
        if raw:
            log_event('cache', {'layer': 'exact', 'hit': True, 'query': query[:60]})
            return json.loads(raw)
    except Exception:
        pass
    return None


def store_exact(query: str, roles: list, customer: str, answer: str, plan: dict) -> None:
    def _store():
        try:
            r.setex(
                _exact_key(query, roles, customer),
                _EXACT_TTL,
                json.dumps({'answer': answer, 'plan': plan}, default=str),
            )
        except Exception:
            pass
    threading.Thread(target=_store, daemon=True).start()


# ── Layer 2: pgvector semantic cache ─────────────────────────────────────────

def get_semantic_cached(query: str, roles: list, customer: str) -> Optional[dict]:
    """Embed query and find a cosine-similar cached answer above threshold."""
    if not _is_cacheable(query):
        return None
    try:
        from services.embedding_service import get_embedding
        emb = get_embedding(query)
        if not emb:
            return None

        from sqlalchemy import text
        from core.db import SessionLocal
        emb_str = '[' + ','.join(str(x) for x in emb) + ']'
        scope = _scope_tag(roles, customer)

        with SessionLocal() as db:
            row = db.execute(text('''
                SELECT answer_text, plan_summary,
                       1 - (query_embedding <=> :emb::vector) AS similarity
                FROM query_cache
                WHERE cache_scope = :scope
                  AND query_embedding IS NOT NULL
                  AND 1 - (query_embedding <=> :emb::vector) > :thresh
                ORDER BY query_embedding <=> :emb::vector
                LIMIT 1
            '''), {'emb': emb_str, 'scope': scope, 'thresh': _SIMILARITY_THRESHOLD}).mappings().first()

            if row:
                db.execute(text('''
                    UPDATE query_cache SET hit_count = hit_count + 1, last_hit_at = NOW()
                    WHERE query_hash = (
                        SELECT query_hash FROM query_cache
                        WHERE cache_scope = :scope AND query_embedding IS NOT NULL
                        ORDER BY query_embedding <=> :emb::vector
                        LIMIT 1
                    )
                '''), {'emb': emb_str, 'scope': scope})
                db.commit()
                log_event('cache', {'layer': 'semantic', 'hit': True,
                                    'similarity': round(float(row['similarity']), 3),
                                    'query': query[:60]})
                return {
                    'answer': row['answer_text'],
                    'plan': json.loads(row['plan_summary']) if row['plan_summary'] else {},
                }
    except Exception:
        pass
    return None


def store_semantic(query: str, roles: list, customer: str,
                   answer: str, plan: dict) -> None:
    """Embed query and store in query_cache table (background)."""
    def _store():
        try:
            from services.embedding_service import get_embedding
            emb = get_embedding(query)
            if not emb:
                return
            emb_str = '[' + ','.join(str(x) for x in emb) + ']'
            scope = _scope_tag(roles, customer)
            qhash = hashlib.sha256((query + scope).encode()).hexdigest()

            from sqlalchemy import text
            from core.db import SessionLocal
            with SessionLocal() as db:
                db.execute(text('''
                    INSERT INTO query_cache
                      (query_text, query_hash, query_embedding, cache_scope,
                       answer_text, plan_summary)
                    VALUES
                      (:qt, :qh, CAST(:emb AS vector), :scope, :answer, :plan)
                    ON CONFLICT (query_hash) DO UPDATE
                      SET hit_count = query_cache.hit_count + 1,
                          last_hit_at = NOW()
                '''), {
                    'qt':     query[:1000],
                    'qh':     qhash,
                    'emb':    emb_str,
                    'scope':  scope,
                    'answer': answer,
                    'plan':   json.dumps(plan, default=str),
                })
                db.commit()
            log_event('cache', {'layer': 'semantic', 'stored': True, 'query': query[:60]})
        except Exception as exc:
            log_event('cache_error', {'layer': 'semantic', 'error': str(exc)[:120], 'query': query[:60]})
    threading.Thread(target=_store, daemon=True).start()


# ── Public interface used by graph_orchestrator ───────────────────────────────

def lookup(query: str, roles: list, customer: str) -> Optional[dict]:
    """Check both layers. Returns {answer, plan} or None on complete miss."""
    hit = get_exact_cached(query, roles, customer)
    if hit:
        return hit
    return get_semantic_cached(query, roles, customer)


def store(query: str, roles: list, customer: str, answer: str, plan: dict) -> None:
    """Persist to both layers (background threads, non-blocking)."""
    store_exact(query, roles, customer, answer, plan)
    store_semantic(query, roles, customer, answer, plan)


def get_cache_stats() -> dict:
    """Aggregate cache stats from the query_cache table for the /cache/stats route."""
    try:
        from sqlalchemy import text
        from core.db import SessionLocal
        with SessionLocal() as db:
            row = db.execute(text('''
                SELECT
                    COUNT(*)                        AS total_entries,
                    COALESCE(SUM(hit_count), 0)     AS total_hits,
                    COALESCE(MAX(last_hit_at), NOW()) AS last_hit_at,
                    COALESCE(MAX(created_at), NOW())  AS oldest_entry
                FROM query_cache
            ''')).mappings().first()
        return dict(row) if row else {}
    except Exception as exc:
        log_event('cache_error', {'action': 'get_stats', 'error': str(exc)[:120]})
        return {}
