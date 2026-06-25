import json
import os
import time
import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from auth.security import get_user_context
from agents.orchestrator import run_agent
from services.keycloak_client import get_password_token

_YAML_PATHS = [
    '/evals/test_queries.yaml',
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../../evals/test_queries.yaml')),
]

router = APIRouter()

class QueryRequest(BaseModel):
    user_query: str = Field(..., max_length=2000)
    session_id: str = 'demo-session'

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post('/query')
def query_agent(request: QueryRequest, user_ctx: dict = Depends(get_user_context)):
    result = run_agent(request.user_query, request.session_id, user_ctx)
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
    return list_all_customers()

@router.get('/issues')
def list_issues_route(user_ctx: dict = Depends(get_user_context)):
    from repositories.issue_repo import list_all_issues
    return list_all_issues()

@router.get('/issues/{issue_id}/history')
def get_issue_history_route(issue_id: int, user_ctx: dict = Depends(get_user_context)):
    from repositories.issue_repo import get_issue_history, list_next_actions_for_issue
    return {
        'history': get_issue_history(issue_id),
        'next_actions': list_next_actions_for_issue(issue_id),
    }

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
                row['grounded'] = (exc.status_code == 403)
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
