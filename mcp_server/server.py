import os
import secrets
from typing import Optional
from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy import create_engine, text

app = FastAPI(title='Acme MCP Server')
engine = create_engine(os.getenv('DATABASE_URL', 'postgresql+psycopg://acme:acme@postgres:5432/acme_ops'))

_MCP_SECRET = os.getenv('MCP_SECRET', '')


def _check_secret(x_mcp_secret: Optional[str] = Header(default=None)):
    """Reject requests that don't carry the correct shared secret.
    If MCP_SECRET is not configured (empty), the check is skipped so the
    server remains accessible for local dev without any env setup."""
    if _MCP_SECRET and not secrets.compare_digest(x_mcp_secret or '', _MCP_SECRET):
        raise HTTPException(status_code=401, detail='Invalid MCP secret')


@app.get('/tools')
def list_tools():
    """Canonical tool registry — single source of truth for tool names and descriptions."""
    return {
        'tools': [
            {'name': 'get_customer_profile',  'description': 'Retrieve customer profile using customer name',      'endpoint': 'GET /customer/{customer_name}'},
            {'name': 'get_open_issues',        'description': 'Retrieve open issues for a customer',               'endpoint': 'GET /issues/{customer_name}'},
            {'name': 'get_issue_history',      'description': 'Summarise issue history for a specific issue',      'endpoint': 'GET /history/{issue_id}'},
            {'name': 'list_all_open_issues',   'description': 'Portfolio-wide issue list with optional filters',   'endpoint': 'GET /issues?severity=&statuses='},
            {'name': 'recommend_next_action',  'description': 'Create a recommended next action for an issue',     'endpoint': '(direct DB — write tool, app-layer RBAC required)'},
        ]
    }


@app.get('/customer/{customer_name}')
def get_customer(customer_name: str, _: None = Depends(_check_secret)):
    """Return customer profile by name. Returns {} if not found."""
    with engine.begin() as conn:
        row = conn.execute(
            text('SELECT id, name, segment, account_owner, health_status FROM customers WHERE LOWER(name)=LOWER(:name)'),
            {'name': customer_name}
        ).mappings().first()
        return dict(row) if row else {}


@app.get('/issues/{customer_name}')
def get_open_issues_for_customer(customer_name: str, _: None = Depends(_check_secret)):
    """Return all open issues for a customer. Returns {issues: []} if none found."""
    with engine.begin() as conn:
        rows = conn.execute(
            text('''
                SELECT i.id, i.title, i.severity, i.status, c.name AS customer_name
                FROM issues i
                JOIN customers c ON i.customer_id = c.id
                WHERE LOWER(c.name) = LOWER(:name)
                  AND LOWER(i.status) = 'open'
                ORDER BY i.id
            '''),
            {'name': customer_name}
        ).mappings().all()
        return {'issues': [dict(r) for r in rows]}


@app.get('/history/{issue_id}')
def get_issue_history(issue_id: int, _: None = Depends(_check_secret)):
    """Return update history for a specific issue. Returns {history: []} if none found."""
    with engine.begin() as conn:
        rows = conn.execute(
            text('''
                SELECT issue_id, update_text, updated_by, created_at
                FROM issue_updates
                WHERE issue_id = :id
                ORDER BY created_at
            '''),
            {'id': issue_id}
        ).mappings().all()
        return {'history': [dict(r) for r in rows]}


@app.get('/issues')
def list_issues_filtered(severity: Optional[str] = None, statuses: Optional[str] = None, _: None = Depends(_check_secret)):
    """
    Portfolio-wide issue list with optional filters.
    severity: optional (critical|high|medium|low)
    statuses: optional comma-separated list (open,in_progress,waiting,resolved)
              defaults to open,in_progress if omitted
    """
    status_list = [s.strip() for s in statuses.split(',')] if statuses else ['open', 'in_progress']

    conditions = []
    params: dict = {}

    if status_list:
        placeholders = ', '.join(f':s{i}' for i in range(len(status_list)))
        conditions.append(f'LOWER(i.status) IN ({placeholders})')
        for i, s in enumerate(status_list):
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
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
        return {'issues': [dict(r) for r in rows]}
