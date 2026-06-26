"""
Cross-session persistent memory — survives session expiry and login gaps.

Two scopes:
  user:{username}       Preferences, communication style, recurring interests
  customer:{name}       Ongoing situations, key contacts, account context

Auto-extraction: after each agent run, a non-blocking LLM call reads the
Q&A pair and stores any cross-session-worthy facts. Facts with low value
or high volatility (e.g. "there are 3 open issues") are intentionally filtered
out — only stable, hard-to-re-derive context is stored.

Injection: get_memories_for_context() returns top-N memories as bullet strings,
injected into the ReAct think prompt so the agent 'remembers' across sessions.
"""
import json
import threading
from typing import Optional

from observability.logging_utils import log_event

_MAX_MEMORIES_INJECTED = 6
_USER_EXPIRY_DAYS = 30
_CUSTOMER_EXPIRY_DAYS = 60


# ── Read ─────────────────────────────────────────────────────────────────────

def get_memories_for_context(username: str, customer_name: str = '') -> list[str]:
    """
    Return up to MAX_MEMORIES_INJECTED memory strings for this user + customer.
    Each string is formatted for direct injection into an LLM prompt.
    """
    try:
        from sqlalchemy import text
        from core.db import SessionLocal

        scopes = [f'user:{username}']
        if customer_name:
            scopes.append(f'customer:{customer_name.lower()}')

        placeholders = ', '.join(f':s{i}' for i in range(len(scopes)))
        params = {f's{i}': s for i, s in enumerate(scopes)}
        params['limit'] = _MAX_MEMORIES_INJECTED

        with SessionLocal() as db:
            rows = db.execute(text(f'''
                SELECT scope, key, value
                FROM persistent_memory
                WHERE scope IN ({placeholders})
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY updated_at DESC
                LIMIT :limit
            '''), params).mappings().all()

        return [
            f"[{r['scope']}] {r['key']}: {r['value']}"
            for r in rows
        ]
    except Exception as exc:
        log_event('memory_warn', {'action': 'get_memories_failed', 'error': str(exc)[:200]})
        return []


# ── Write ─────────────────────────────────────────────────────────────────────

def store_memory(scope: str, key: str, value: str,
                 source: str = 'auto_extracted',
                 expires_days: Optional[int] = None) -> None:
    try:
        from sqlalchemy import text
        from core.db import SessionLocal

        with SessionLocal() as db:
            db.execute(text('''
                INSERT INTO persistent_memory (scope, key, value, source, expires_at)
                VALUES (:scope, :key, :value, :source,
                        CASE WHEN :days IS NOT NULL
                             THEN NOW() + (:days * INTERVAL '1 day')
                             ELSE NULL END)
                ON CONFLICT (scope, key) DO UPDATE
                  SET value      = EXCLUDED.value,
                      source     = EXCLUDED.source,
                      updated_at = NOW(),
                      expires_at = CASE WHEN :days IS NOT NULL
                                        THEN NOW() + (:days * INTERVAL '1 day')
                                        ELSE persistent_memory.expires_at END
            '''), {'scope': scope, 'key': key, 'value': value[:500],
                   'source': source, 'days': expires_days})
            db.commit()
    except Exception as exc:
        log_event('memory_warn', {'action': 'store_memory_failed', 'scope': scope,
                                  'key': key, 'error': str(exc)[:200]})


# ── Auto-extraction ───────────────────────────────────────────────────────────

def _extract_memories_llm(query: str, answer: str,
                           username: str, customer_name: str) -> list[dict]:
    """
    Call the LLM to extract cross-session-worthy facts from the conversation.
    Returns a list of {scope, key, value, expires_days} dicts.
    Only called when OPENAI_API_KEY is configured.
    """
    from core.config import OPENAI_API_KEY, OPENAI_MODEL
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'replace_me':
        return []

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, max_retries=3)

    system = f"""You extract cross-session memory facts from a customer-success assistant conversation.
Rules:
- Only extract facts that would be useful IN FUTURE sessions (not just this one)
- DO NOT store: current issue counts, current health status (too volatile), dates, numbers that change
- DO store: ongoing situations, known escalations, communication preferences, key contacts, relationship context
- Scope 'user:{username}' for user preferences; 'customer:{customer_name.lower()}' for account context
- expires_days: 30 for user preferences, 60 for customer context, null for long-lived facts
- Maximum 3 facts; return [] if nothing truly cross-session-worthy

Return JSON array: [{{"scope":"...","key":"...","value":"...","expires_days":60}}]"""

    user_msg = f"Query: {query[:300]}\nAnswer summary: {answer[:400]}"

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            response_format={'type': 'json_object'},
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': user_msg},
            ],
            max_tokens=400,
        )
        raw_content = resp.choices[0].message.content
        data = json.loads(raw_content)
        if isinstance(data, list):
            facts = data
        elif isinstance(data, dict) and data.get('scope') and data.get('key'):
            facts = [data]  # LLM returned a single flat fact object
        else:
            facts = data.get('facts', data.get('memories', data.get('memory', data.get('result', []))))
        valid = [f for f in facts if isinstance(f, dict) and f.get('scope') and f.get('key')]
        log_event('memory', {'action': 'llm_extract', 'raw_facts': len(facts), 'valid': len(valid)})
        return valid
    except Exception as exc:
        log_event('memory_error', {'action': 'llm_extract_failed', 'error': str(exc)[:200]})
        return []


def extract_and_store_async(query: str, answer: str,
                             username: str, customer_name: str) -> None:
    """
    Non-blocking: spawn a daemon thread to extract and persist memories.
    Called after each agent run — never on the critical path.
    """
    if not answer or len(answer) < 60:
        return  # skip trivial responses

    def _run():
        facts = _extract_memories_llm(query, answer, username, customer_name)
        for f in facts:
            store_memory(
                scope=f['scope'],
                key=f['key'],
                value=f['value'],
                source='auto_extracted',
                expires_days=f.get('expires_days'),
            )
        if facts:
            log_event('memory', {
                'action': 'extracted',
                'count': len(facts),
                'user': username,
                'customer': customer_name,
            })

    threading.Thread(target=_run, daemon=True, name='memory-extract').start()
