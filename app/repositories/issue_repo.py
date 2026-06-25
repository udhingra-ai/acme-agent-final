from sqlalchemy import text
from core.db import SessionLocal


def _rls_owner(user_ctx: dict) -> tuple:
    """Return (apply_filter, owner). Filter rows by account_owner for sales_user role."""
    if not user_ctx:
        return False, ''
    roles = user_ctx.get('roles', [])
    if 'admin' in roles or 'support_user' in roles:
        return False, ''
    return True, user_ctx.get('username', '')


def list_all_issues(user_ctx: dict = None):
    apply_rls, owner = _rls_owner(user_ctx)
    rls_clause = 'WHERE c.account_owner = :owner' if apply_rls else ''
    params = {'owner': owner} if apply_rls else {}
    sql = f'''
    SELECT i.id, i.title, i.severity, i.status, i.created_at,
           c.name AS customer_name, c.id AS customer_id
    FROM issues i
    JOIN customers c ON i.customer_id = c.id
    {rls_clause}
    ORDER BY i.id DESC
    '''
    with SessionLocal() as db:
        rows = db.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]


def get_all_issues_filtered(statuses: list = None, severity: str = None,
                             user_ctx: dict = None):
    """Return issues across all customers, optionally filtered by status list and/or severity."""
    apply_rls, owner = _rls_owner(user_ctx)
    conditions = []
    params = {}

    if apply_rls:
        conditions.append('c.account_owner = :rls_owner')
        params['rls_owner'] = owner
    if statuses:
        placeholders = ', '.join(f':s{i}' for i in range(len(statuses)))
        conditions.append(f'LOWER(i.status) IN ({placeholders})')
        for i, s in enumerate(statuses):
            params[f's{i}'] = s.lower()
    if severity:
        conditions.append('LOWER(i.severity) = :severity')
        params['severity'] = severity.lower()

    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
    sql = f'''
    SELECT i.id, i.title, i.severity, i.status, i.created_at,
           c.name AS customer_name, c.health_status
    FROM issues i
    JOIN customers c ON i.customer_id = c.id
    {where}
    ORDER BY
        CASE LOWER(i.severity) WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
        c.name
    '''
    with SessionLocal() as db:
        rows = db.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]


def list_next_actions_for_issue(issue_id: int):
    sql = '''
    SELECT id, issue_id, action_text, owner, due_date, status, created_at
    FROM next_actions WHERE issue_id = :issue_id ORDER BY created_at DESC
    '''
    with SessionLocal() as db:
        rows = db.execute(text(sql), {'issue_id': issue_id}).mappings().all()
        return [dict(r) for r in rows]


def get_open_issues_for_customer(customer_name: str, user_ctx: dict = None):
    apply_rls, owner = _rls_owner(user_ctx)
    rls_clause = 'AND c.account_owner = :owner' if apply_rls else ''
    params = {'name': customer_name}
    if apply_rls:
        params['owner'] = owner
    sql = f'''
    SELECT i.id, i.title, i.severity, i.status, c.name as customer_name
    FROM issues i
    JOIN customers c ON i.customer_id = c.id
    WHERE LOWER(c.name)=LOWER(:name) AND LOWER(i.status)=\'open\' {rls_clause}
    ORDER BY i.id
    '''
    with SessionLocal() as db:
        rows = db.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]


def get_issue_by_id(issue_id: int) -> dict | None:
    sql = '''
    SELECT i.id, i.title, i.severity, i.status, c.name AS customer_name
    FROM issues i
    JOIN customers c ON i.customer_id = c.id
    WHERE i.id = :issue_id
    '''
    with SessionLocal() as db:
        row = db.execute(text(sql), {'issue_id': issue_id}).mappings().first()
        return dict(row) if row else None


def get_issue_history(issue_id: int):
    sql = '''
    SELECT iu.issue_id, iu.update_text, iu.updated_by, iu.created_at
    FROM issue_updates iu
    WHERE iu.issue_id = :issue_id
    ORDER BY iu.created_at
    '''
    with SessionLocal() as db:
        rows = db.execute(text(sql), {'issue_id': issue_id}).mappings().all()
        return [dict(r) for r in rows]


def semantic_search_issues(query_embedding: list, limit: int = 5,
                           user_ctx: dict = None) -> list:
    """
    Return issues ranked by cosine similarity to the query embedding.
    Requires pgvector extension and non-NULL embeddings on the issues table.
    Returns [] gracefully if embeddings are absent.
    """
    apply_rls, owner = _rls_owner(user_ctx)
    rls_clause = 'AND c.account_owner = :owner' if apply_rls else ''
    emb_str = '[' + ','.join(str(x) for x in query_embedding) + ']'
    params = {'emb': emb_str, 'limit': limit}
    if apply_rls:
        params['owner'] = owner
    sql = f'''
    SELECT i.id, i.title, i.severity, i.status, c.name AS customer_name,
           ROUND((1 - (embedding <=> CAST(:emb AS vector)))::numeric, 3) AS similarity
    FROM issues i
    JOIN customers c ON i.customer_id = c.id
    WHERE embedding IS NOT NULL {rls_clause}
    ORDER BY embedding <=> CAST(:emb AS vector)
    LIMIT :limit
    '''
    try:
        with SessionLocal() as db:
            rows = db.execute(text(sql), params).mappings().all()
            return [dict(r) for r in rows]
    except Exception:
        return []


def create_next_action(issue_id: int, action_text: str, owner: str):
    sql = '''
    INSERT INTO next_actions (issue_id, action_text, owner, due_date, status)
    VALUES (:issue_id, :action_text, :owner, CURRENT_DATE + INTERVAL '1 day', 'proposed')
    RETURNING id, issue_id, action_text, owner, due_date, status
    '''
    with SessionLocal() as db:
        row = db.execute(text(sql), {'issue_id': issue_id, 'action_text': action_text, 'owner': owner}).mappings().first()
        db.commit()
        return dict(row)
