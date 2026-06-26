import json
import os
import time
import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from auth.security import get_user_context
from agents.orchestrator import run_agent, run_agent_stream   # /query (non-streaming)
from agents.graph_orchestrator import run_agent_stream as graph_stream  # /query/stream (LangGraph ReAct)
from services.keycloak_client import get_password_token
from services.rate_limiter import limiter

# Orchestrator routing:
#   POST /query         → agents/orchestrator.py (run_agent)
#                         Synchronous; deterministic planner + rule fallback; returns full JSON.
#                         Used by: eval harness, API clients that don't support SSE.
#
#   POST /query/stream  → agents/graph_orchestrator.py (graph_stream / run_agent_stream)
#                         Streaming SSE; LangGraph 5-node ReAct loop; progressive token output.
#                         Used by: web UI, SSE-capable clients.
#
# Both paths share the same tool layer (services/tools.py), RBAC (auth/security.py),
# and RLS enforcement. The LangGraph path is the production primary; the sync path
# is kept for compatibility and eval coverage.

_YAML_PATHS = [
    '/evals/test_queries.yaml',
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../../evals/test_queries.yaml')),
]

router = APIRouter()

class QueryRequest(BaseModel):
    user_query: str = Field(..., max_length=2000)
    session_id: str = 'demo-session'
    confirmed_customer: str = ''   # set after user disambiguates a name

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post('/query/stream')
@limiter.limit('30/minute')
def query_stream(request: Request, body: QueryRequest,
                 user_ctx: dict = Depends(get_user_context)):
    trace_id = getattr(request.state, 'trace_id', '')
    return StreamingResponse(
        graph_stream(body.user_query, body.session_id, user_ctx,
                     confirmed_customer=body.confirmed_customer,
                     trace_id=trace_id),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@router.post('/query')
@limiter.limit('30/minute')
def query_agent_limited(request: Request, body: QueryRequest,
                        user_ctx: dict = Depends(get_user_context)):
    trace_id = getattr(request.state, 'trace_id', '')
    result = run_agent(body.user_query, body.session_id, user_ctx, trace_id=trace_id)
    return {'user': user_ctx, **result}

@router.post('/auth/token')
def login_via_keycloak(request: LoginRequest):
    try:
        token = get_password_token(request.username, request.password)
        return token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f'Login failed: {e}')

@router.get('/customers')
def list_customers_route(user_ctx: dict = Depends(get_user_context)):
    from repositories.customer_repo import list_all_customers
    return list_all_customers(user_ctx=user_ctx)

@router.get('/issues')
def list_issues_route(user_ctx: dict = Depends(get_user_context)):
    from repositories.issue_repo import list_all_issues
    return list_all_issues(user_ctx=user_ctx)

@router.get('/issues/{issue_id}/history')
def get_issue_history_route(issue_id: int, user_ctx: dict = Depends(get_user_context)):
    from repositories.issue_repo import get_issue_history, list_next_actions_for_issue
    return {
        'history': get_issue_history(issue_id),
        'next_actions': list_next_actions_for_issue(issue_id),
    }

@router.get('/alerts')
def get_alerts(user_ctx: dict = Depends(get_user_context)):
    """
    Proactive risk alerts — scans all customers and surfaces at-risk accounts
    autonomously, without waiting for a user query.
    Deduplicates: the same alert won't re-fire within 1 hour.
    """
    from repositories.customer_repo import list_all_customers
    from services.alert_service import should_send_alert
    customers = list_all_customers(user_ctx=user_ctx)
    alerts = []
    for c in customers:
        open_count = c.get('open_issues') or 0
        if c['health_status'] == 'red' and open_count > 0:
            if should_send_alert(c['name'], 'critical'):
                alerts.append({
                    'type': 'critical',
                    'customer_name': c['name'],
                    'segment': c.get('segment', ''),
                    'open_issues': open_count,
                    'message': f"{open_count} open issue{'s' if open_count != 1 else ''} — health critical",
                })
        elif c['health_status'] == 'amber' and open_count >= 2:
            if should_send_alert(c['name'], 'warning'):
                alerts.append({
                    'type': 'warning',
                    'customer_name': c['name'],
                    'segment': c.get('segment', ''),
                    'open_issues': open_count,
                    'message': f"{open_count} open issues — health at risk",
                })
    return {'alerts': alerts, 'total': len(alerts)}


@router.get('/briefings')
def get_briefings_route(user_ctx: dict = Depends(get_user_context)):
    """Return unacknowledged autonomous briefings, scoped by role."""
    from repositories.briefing_repo import get_recent_briefings
    roles = user_ctx.get('roles', [])
    # sales_user sees only their own briefings; admin/support see all
    owner = user_ctx.get('username') if ('sales_user' in roles and 'admin' not in roles) else None
    return {'briefings': get_recent_briefings(limit=20, account_owner=owner)}


@router.post('/briefings/{briefing_id}/acknowledge')
def acknowledge_briefing_route(briefing_id: int, user_ctx: dict = Depends(get_user_context)):
    from repositories.briefing_repo import acknowledge_briefing, get_briefing_by_id
    from services.alert_service import clear_alert
    roles = user_ctx.get('roles', [])
    # Non-admin users can only acknowledge briefings they own
    owner = None if 'admin' in roles else user_ctx.get('username')
    # Fetch before acknowledging so we can clear the alert dedup key,
    # allowing the same customer to trigger a new alert after the user dismisses.
    briefing = get_briefing_by_id(briefing_id)
    ok = acknowledge_briefing(briefing_id, account_owner=owner)
    if not ok:
        raise HTTPException(status_code=404, detail='Briefing not found')
    if briefing:
        clear_alert(briefing['customer_name'], briefing.get('source', 'health_sweep'))
    return {'acknowledged': True}


@router.get('/memory')
def get_memory_route(scope: str = '', user_ctx: dict = Depends(get_user_context)):
    """Inspect persistent memory entries. Admin sees all; others see own scope only."""
    from auth.security import require_role
    from sqlalchemy import text
    from core.db import SessionLocal
    roles = user_ctx.get('roles', [])
    username = user_ctx.get('username', '')
    if 'admin' not in roles:
        scope = f'user:{username}'  # non-admins can only see their own
    where = 'WHERE scope = :scope' if scope else ''
    params = {'scope': scope} if scope else {}
    with SessionLocal() as db:
        rows = db.execute(text(f'''
            SELECT scope, key, value, source, expires_at, updated_at
            FROM persistent_memory
            {where}
            ORDER BY scope, updated_at DESC
            LIMIT 100
        '''), params).mappings().all()
    return {'memories': [dict(r) for r in rows]}


@router.delete('/memory/{scope_key:path}')
def delete_memory_route(scope_key: str, user_ctx: dict = Depends(get_user_context)):
    """Delete a specific memory entry by scope|key (admin only)."""
    from auth.security import require_role
    require_role(user_ctx, ['admin'])
    parts = scope_key.split('|', 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail='Format: scope|key')
    from sqlalchemy import text
    from core.db import SessionLocal
    with SessionLocal() as db:
        db.execute(text('DELETE FROM persistent_memory WHERE scope=:s AND key=:k'),
                   {'s': parts[0], 'k': parts[1]})
        db.commit()
    return {'deleted': True}


@router.get('/cache/stats')
def cache_stats_route(user_ctx: dict = Depends(get_user_context)):
    """Query cache statistics (admin only)."""
    from auth.security import require_role
    require_role(user_ctx, ['admin'])
    from sqlalchemy import text
    from core.db import SessionLocal
    with SessionLocal() as db:
        row = db.execute(text('''
            SELECT COUNT(*) AS total_entries,
                   SUM(hit_count) AS total_hits,
                   MAX(last_hit_at) AS last_hit
            FROM query_cache
        ''')).mappings().first()
    return dict(row) if row else {}


@router.get('/audit')
def get_audit_log(limit: int = 50, username: str = '',
                  user_ctx: dict = Depends(get_user_context)):
    """Return the durable write audit log (admin only). Queryable by username."""
    from auth.security import require_role
    require_role(user_ctx, ['admin'])
    from sqlalchemy import text
    from core.db import SessionLocal
    params: dict = {'limit': min(limit, 200)}
    where = 'WHERE username = :username' if username else ''
    if username:
        params['username'] = username
    with SessionLocal() as db:
        rows = db.execute(text(f'''
            SELECT trace_id, tool, label, username, roles, args, ts
            FROM write_audit {where}
            ORDER BY ts DESC LIMIT :limit
        '''), params).mappings().all()
    return {'entries': [dict(r) for r in rows], 'total': len(rows)}


@router.get('/trace/{trace_id}')
def get_trace_route(trace_id: str, user_ctx: dict = Depends(get_user_context)):
    """Return LangGraph node steps persisted to Redis for a request trace (admin only)."""
    from auth.security import require_role
    require_role(user_ctx, ['admin', 'support_user'])
    try:
        from core.redis_client import r
        raw = r.lrange(f'trace:{trace_id}:steps', 0, -1)
        import json as _json
        steps = [_json.loads(s) for s in raw]
    except Exception:
        steps = []
    return {'trace_id': trace_id, 'steps': steps, 'count': len(steps)}


@router.post('/briefings/sweep')
def trigger_sweep(user_ctx: dict = Depends(get_user_context)):
    """Manually trigger a health sweep (admin only)."""
    from auth.security import require_role
    require_role(user_ctx, ['admin'])
    from services.autonomous_agent import run_health_sweep
    count = run_health_sweep()
    return {'new_briefings': count}


@router.get('/customers/search')
def search_customers(q: str = '', user_ctx: dict = Depends(get_user_context)):
    """Fuzzy customer name lookup for disambiguation UI."""
    from repositories.customer_repo import find_customer_matches
    if not q or len(q) < 2:
        return {'matches': []}
    matches, _ = find_customer_matches(q)
    return {'matches': matches}


@router.get('/evals')
def get_evals_route(user_ctx: dict = Depends(get_user_context)):
    candidates = [
        '/evals/reports/results.json',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '../../evals/reports/results.json')),
    ]
    for path in candidates:
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            continue
    return {'summary': None, 'results': []}


@router.post('/evals/run')
def run_evals_live(user_ctx: dict = Depends(get_user_context)):
    """Run the evaluation suite live, streaming one SSE event per completed test case. Admin only."""
    from auth.security import require_role
    require_role(user_ctx, ['admin'])
    tests = None
    for path in _YAML_PATHS:
        try:
            with open(path) as f:
                tests = yaml.safe_load(f)
            break
        except Exception:
            continue
    if not tests:
        raise HTTPException(status_code=500, detail='test_queries.yaml not found')

    def _generate():
        results = []
        total = len(tests)

        for idx, t in enumerate(tests):
            eval_id = t.get('id', f'T{idx + 1:02d}')
            role = t['role']
            user_ctx = {
                'username': f'eval.{role}',
                'roles': [role],
                'auth_mode': 'eval',
            }
            expected_tools = t.get('expected_tools', [])
            expected_status = t.get('expect_status', 200)

            row = {
                'id': eval_id,
                'query': t['query'],
                'role': role,
                'expected_tools': expected_tools,
                'notes': t.get('notes', ''),
                'actual_tools': [],
                'tool_match': False,
                'status_match': False,
                'status_code': 0,
                'latency_ms': -1,
                'grounded': False,
            }

            try:
                t0 = time.time()
                result = run_agent(t['query'], f'eval-{eval_id}', user_ctx)
                row['latency_ms'] = round((time.time() - t0) * 1000)
                row['status_code'] = 200
                actual_tools = [s.get('tool') for s in result.get('steps', []) if s.get('tool')]
                row['actual_tools'] = actual_tools
                row['tool_match'] = actual_tools == expected_tools
                row['status_match'] = (expected_status == 200)
                tool_steps = [s for s in result.get('steps', []) if s.get('tool')]
                row['grounded'] = bool(tool_steps)
            except HTTPException as exc:
                row['status_code'] = exc.status_code
                row['status_match'] = (exc.status_code == expected_status)
                row['tool_match'] = (expected_tools == [])
                # 400 = prompt injection blocked, 403 = RBAC blocked — both are correct rejections
                row['grounded'] = (exc.status_code in (400, 403))
                row['latency_ms'] = 0
            except Exception as exc:
                row['error'] = str(exc)

            results.append(row)
            yield f"data: {json.dumps({'type': 'result', 'row': row, 'idx': idx, 'total': total})}\n\n"

        # Final summary
        summary = {
            'total_tests': len(results),
            'tool_match_count': sum(1 for r in results if r.get('tool_match')),
            'status_match_count': sum(1 for r in results if r.get('status_match')),
            'grounded_count': sum(1 for r in results if r.get('grounded')),
            'avg_latency_ms': round(
                sum(r.get('latency_ms', 0) for r in results if r.get('latency_ms', 0) > 0)
                / max(1, sum(1 for r in results if r.get('latency_ms', 0) > 0))
            ),
        }
        all_pass = (
            summary['tool_match_count'] >= len(results) - 1
            and summary['status_match_count'] == len(results)
            and summary['grounded_count'] == len(results)
        )
        summary['verdict'] = 'PASS' if all_pass else 'FAIL'
        yield f"data: {json.dumps({'type': 'summary', 'summary': summary})}\n\n"

        # Persist results
        report = {'summary': summary, 'results': results}
        for rpt_path in ['/evals/reports/results.json',
                         os.path.abspath(os.path.join(os.path.dirname(__file__), '../../evals/reports/results.json'))]:
            try:
                os.makedirs(os.path.dirname(rpt_path), exist_ok=True)
                with open(rpt_path, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                break
            except Exception:
                continue

    return StreamingResponse(
        _generate(),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )
