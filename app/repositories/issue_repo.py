from sqlalchemy import text
from core.db import SessionLocal


def list_all_issues():
    sql = '''
    SELECT i.id, i.title, i.severity, i.status, i.created_at,
           c.name AS customer_name, c.id AS customer_id
    FROM issues i
    JOIN customers c ON i.customer_id = c.id
    ORDER BY i.id DESC
    '''
    with SessionLocal() as db:
        rows = db.execute(text(sql)).mappings().all()
        return [dict(r) for r in rows]


def get_all_issues_filtered(statuses: list = None, severity: str = None):
    """Return issues across all customers, optionally filtered by status list and/or severity."""
    conditions = []
    params = {}

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


def get_open_issues_for_customer(customer_name: str):
    sql = '''
    SELECT i.id, i.title, i.severity, i.status, c.name as customer_name
    FROM issues i
    JOIN customers c ON i.customer_id = c.id
    WHERE LOWER(c.name)=LOWER(:name) AND LOWER(i.status)='open'
    ORDER BY i.id
    '''
    with SessionLocal() as db:
        rows = db.execute(text(sql), {'name': customer_name}).mappings().all()
        return [dict(r) for r in rows]


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
