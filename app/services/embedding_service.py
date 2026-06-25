"""
Embedding service for semantic (RAG) search over issue titles.
Uses OpenAI text-embedding-3-small (1536 dims).
All functions degrade gracefully when OPENAI_API_KEY is absent.
"""
from typing import Optional
from core.config import OPENAI_API_KEY

_EMBED_MODEL = 'text-embedding-3-small'
_client = None


def _get_client():
    global _client
    if _client is None and OPENAI_API_KEY and OPENAI_API_KEY != 'replace_me':
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def get_embedding(text: str) -> Optional[list]:
    """Return a 1536-dim embedding list or None if API key is not configured."""
    client = _get_client()
    if not client:
        return None
    try:
        resp = client.embeddings.create(model=_EMBED_MODEL, input=text[:8000])
        return resp.data[0].embedding
    except Exception:
        return None


def embed_batch(texts: list[str]) -> list[Optional[list]]:
    """Embed a list of strings in one API call. Returns parallel list of embeddings or Nones."""
    client = _get_client()
    if not client:
        return [None] * len(texts)
    try:
        resp = client.embeddings.create(model=_EMBED_MODEL, input=[t[:8000] for t in texts])
        return [r.embedding for r in resp.data]
    except Exception:
        return [None] * len(texts)


def backfill_issue_embeddings():
    """
    Embed any issues whose embedding column is NULL.
    Called once at app startup; safe to call repeatedly (idempotent).
    Silently skips when OpenAI key is absent.
    """
    client = _get_client()
    if not client:
        return

    from sqlalchemy import text
    from core.db import SessionLocal

    try:
        with SessionLocal() as db:
            rows = db.execute(
                text('SELECT id, title FROM issues WHERE embedding IS NULL ORDER BY id')
            ).mappings().all()
            if not rows:
                return

            titles = [r['title'] for r in rows]
            embeddings = embed_batch(titles)

            for row, emb in zip(rows, embeddings):
                if emb is None:
                    continue
                emb_str = '[' + ','.join(str(x) for x in emb) + ']'
                db.execute(
                    text('UPDATE issues SET embedding = CAST(:e AS vector) WHERE id = :id'),
                    {'e': emb_str, 'id': row['id']}
                )
            db.commit()
    except Exception:
        pass  # Non-fatal — semantic search just returns empty results
