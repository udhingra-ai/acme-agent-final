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


def list_all_customers():
    sql = '''
    SELECT c.id, c.name, c.segment, c.account_owner, c.health_status,
           COUNT(CASE WHEN LOWER(i.status) = 'open' THEN 1 END) AS open_issues
    FROM customers c
    LEFT JOIN issues i ON i.customer_id = c.id
    GROUP BY c.id, c.name, c.segment, c.account_owner, c.health_status
    ORDER BY c.name
    '''
    with SessionLocal() as db:
        rows = db.execute(text(sql)).mappings().all()
        return [dict(r) for r in rows]
