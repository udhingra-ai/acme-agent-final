import os
from fastapi import FastAPI
from sqlalchemy import create_engine, text

app = FastAPI(title='Acme MCP Server')
engine = create_engine(os.getenv('DATABASE_URL', 'postgresql+psycopg://acme:acme@postgres:5432/acme_ops'))


@app.get('/tools')
def list_tools():
    """Canonical tool registry — single source of truth for tool names and descriptions."""
    return {
        'tools': [
            {'name': 'get_customer_profile',  'description': 'Retrieve customer profile using customer name',       'endpoint': 'GET /customer/{customer_name}'},
            {'name': 'get_open_issues',        'description': 'Retrieve open issues for a customer',                'endpoint': 'GET /issues/{customer_name}'},
            {'name': 'get_issue_history',      'description': 'Summarise issue history for a specific issue',       'endpoint': '(direct DB — not yet routed via MCP)'},
            {'name': 'recommend_next_action',  'description': 'Create a recommended next action for an issue',      'endpoint': '(direct DB — write tool, app-layer RBAC required)'},
        ]
    }


@app.get('/customer/{customer_name}')
def get_customer(customer_name: str):
    """Return customer profile by name. Returns {} if not found."""
    with engine.begin() as conn:
        row = conn.execute(
            text('SELECT id, name, segment, account_owner, health_status FROM customers WHERE LOWER(name)=LOWER(:name)'),
            {'name': customer_name}
        ).mappings().first()
        return dict(row) if row else {}


@app.get('/issues/{customer_name}')
def get_open_issues(customer_name: str):
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
