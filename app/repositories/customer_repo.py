from __future__ import annotations

from sqlalchemy import text
from core.db import SessionLocal

# Words that carry no customer identity — stripped before fuzzy matching
_NOISE_WORDS = {
    'client', 'customer', 'account', 'the', 'a', 'an', 'my', 'our',
    'their', 'for', 'of', 'at', 'on', 'in', 'and', 'or', 'with',
}


def get_customer_by_name(customer_name: str):
    with SessionLocal() as db:
        row = db.execute(
            text('SELECT id, name, segment, account_owner, health_status FROM customers WHERE LOWER(name)=LOWER(:name)'),
            {'name': customer_name}
        ).mappings().first()
        return dict(row) if row else None


def resolve_customer_name(partial: str) -> str:
    """
    Resolve a partial or fuzzy customer name to the canonical DB name.

    Tier 1 — exact LOWER match
    Tier 2 — word-by-word LIKE substring (handles "nexus client" → "Nexus Payments Ltd")
    Tier 3 — pg_trgm similarity score (handles typos / transpositions)
    """
    if not partial:
        return partial

    with SessionLocal() as db:
        # Tier 1: exact
        row = db.execute(
            text('SELECT name FROM customers WHERE LOWER(name)=LOWER(:n)'),
            {'n': partial}
        ).mappings().first()
        if row:
            return row['name']

        # Tier 2: word-by-word ILIKE — try each meaningful word as a substring
        words = [w for w in partial.lower().split() if w not in _NOISE_WORDS and len(w) >= 3]
        for word in words:
            row = db.execute(
                text("SELECT name FROM customers WHERE LOWER(name) LIKE '%' || :w || '%' LIMIT 1"),
                {'w': word}
            ).mappings().first()
            if row:
                return row['name']

        # Tier 3: pg_trgm similarity — best fuzzy match above threshold
        row = db.execute(
            text('''
                SELECT name, similarity(LOWER(name), LOWER(:n)) AS sim
                FROM customers
                ORDER BY sim DESC
                LIMIT 1
            '''),
            {'n': partial}
        ).mappings().first()
        if row and row['sim'] > 0.1:
            return row['name']

    # No match found — return as-is so the caller can handle the miss gracefully
    return partial


def find_customer_matches(partial: str) -> tuple:
    """
    Return (matches: list[str], exact: bool).
    exact=True means the input already matched a DB name precisely — no confirmation needed.
    exact=False means the match was fuzzy — the caller should ask the user to confirm.
    """
    if not partial:
        return [], True

    with SessionLocal() as db:
        # Exact match — no disambiguation needed
        exact = db.execute(
            text('SELECT name FROM customers WHERE LOWER(name)=LOWER(:n)'),
            {'n': partial}
        ).mappings().first()
        if exact:
            return [exact['name']], True

        # Word-by-word ILIKE — collect all matches
        words = [w for w in partial.lower().split() if w not in _NOISE_WORDS and len(w) >= 3]
        matches: set = set()
        for word in words:
            rows = db.execute(
                text("SELECT name FROM customers WHERE LOWER(name) LIKE '%' || :w || '%'"),
                {'w': word}
            ).mappings().all()
            matches.update(r['name'] for r in rows)

        # pg_trgm full-string fallback — picks up typos in multi-word names
        rows = db.execute(
            text('''
                SELECT name, similarity(LOWER(name), LOWER(:n)) AS sim
                FROM customers
                WHERE similarity(LOWER(name), LOWER(:n)) > 0.15
                ORDER BY sim DESC
                LIMIT 3
            '''),
            {'n': partial}
        ).mappings().all()
        matches.update(r['name'] for r in rows)

        # Word-level trigram — "nexi" matches the word "Nexus" inside "Nexus Payments Ltd"
        # This handles short misspelled fragments that don't resemble the full name
        rows = db.execute(
            text('''
                SELECT DISTINCT name
                FROM customers
                WHERE EXISTS (
                    SELECT 1
                    FROM regexp_split_to_table(LOWER(name), '\\s+') AS word
                    WHERE similarity(word, LOWER(:n)) > 0.35
                )
                LIMIT 3
            '''),
            {'n': partial}
        ).mappings().all()
        matches.update(r['name'] for r in rows)

        return sorted(matches), False


def _rls_owner(user_ctx: dict) -> tuple:
    """Return (apply_filter, owner). Filter rows by account_owner for sales_user role."""
    if not user_ctx:
        return False, ''
    roles = user_ctx.get('roles', [])
    if 'admin' in roles or 'support_user' in roles:
        return False, ''
    return True, user_ctx.get('username', '')


def get_allowed_customer_names(user_ctx: dict) -> set | None:
    """
    Return set of customer names visible to this user, or None if unrestricted.
    Used to filter MCP results (which bypass row-level SQL) on the app side.
    """
    apply_rls, owner = _rls_owner(user_ctx)
    if not apply_rls:
        return None  # None = no restriction
    with SessionLocal() as db:
        rows = db.execute(
            text('SELECT name FROM customers WHERE account_owner = :owner'),
            {'owner': owner}
        ).mappings().all()
        return {r['name'] for r in rows}


def list_all_customers(user_ctx: dict = None):
    apply_rls, owner = _rls_owner(user_ctx)
    rls_clause = 'WHERE c.account_owner = :owner' if apply_rls else ''
    params = {'owner': owner} if apply_rls else {}
    sql = f'''
    SELECT c.id, c.name, c.segment, c.account_owner, c.health_status,
           COUNT(CASE WHEN LOWER(i.status) = 'open' THEN 1 END) AS open_issues
    FROM customers c
    LEFT JOIN issues i ON i.customer_id = c.id
    {rls_clause}
    GROUP BY c.id, c.name, c.segment, c.account_owner, c.health_status
    ORDER BY c.name
    '''
    with SessionLocal() as db:
        rows = db.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]
