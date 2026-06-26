"""
Evaluation harness for Acme Operations Agentic Assistant.

Usage:
    python evals/runner.py                  # test both /query and /query/stream
    python evals/runner.py --sync-only      # test /query only
    python evals/runner.py --stream-only    # test /query/stream only

Writes results to evals/reports/results.json.
Expected baseline: 32/32 status_match, ≥31/32 tool_match, 32/32 grounded.

Sync path  (/query):          exact tool_match (planner is deterministic)
Stream path (/query/stream):  subset tool_match (ReAct may call extra tools)
T08 stream: uses stream_user=alice.sales so RLS exposes issues and RBAC fires.
"""
import sys
import time
import yaml
import json
import requests
import os

BASE_URL = os.getenv('APP_URL', 'http://localhost:8000')

_args = sys.argv[1:]
_run_sync   = '--stream-only' not in _args
_run_stream = '--sync-only'   not in _args


def _flush_query_cache():
    """Delete all qcache:* keys from Redis so evals run against live tools, not cached answers."""
    import subprocess
    try:
        result = subprocess.run(
            ['docker', 'exec', 'acme-redis', 'redis-cli', '-a', 'acme-redis-local',
             '--no-auth-warning', 'EVAL',
             "local keys = redis.call('KEYS','qcache:*') if #keys>0 then return redis.call('DEL',unpack(keys)) else return 0 end",
             '0'],
            capture_output=True, text=True, timeout=5
        )
        count = result.stdout.strip()
        print(f'  Cache flushed: {count} qcache keys removed')
    except Exception as e:
        print(f'  Cache flush skipped ({e})')


with open('evals/test_queries.yaml') as f:
    tests = yaml.safe_load(f)


def _eval_sync(t: dict, eval_id: str) -> dict:
    """Run a test case against POST /query (sync orchestrator path)."""
    headers = {'x-role': t['role'], 'x-user': f"eval.{t['role']}"}
    payload = {'user_query': t['query'], 'session_id': f'eval-{eval_id}'}
    row = {
        'id': eval_id, 'path': '/query',
        'query': t['query'], 'role': t['role'],
        'expected_tools': t.get('expected_tools', []),
        'expect_status': t.get('expect_status'),
        'notes': t.get('notes', ''),
    }
    try:
        t0 = time.time()
        r = requests.post(f'{BASE_URL}/query', json=payload, headers=headers, timeout=30)
        row['latency_ms'] = round((time.time() - t0) * 1000)
        row['status_code'] = r.status_code
        try:
            body = r.json()
        except Exception:
            body = {'raw': r.text}
        row['body'] = body
        actual_tools = [s.get('tool') for s in body.get('steps', []) if s.get('tool')]
        row['actual_tools'] = actual_tools
        row['tool_match'] = actual_tools == t.get('expected_tools', [])
        row['status_match'] = r.status_code == t.get('expect_status')
        _set_grounded(row, r.status_code, body)
    except Exception as e:
        _fail_row(row, e)
    return row


def _eval_stream(t: dict, eval_id: str) -> dict:
    """
    Run a test case against POST /query/stream (LangGraph ReAct SSE path).

    Parses SSE events to extract tool names (from tool_result events) and
    final status. The stream path is the production-primary path for the web UI.
    """
    # stream_user overrides x-user for cases (e.g. T08) where the default
    # eval user doesn't own the named customer — RLS would hide issues and
    # RBAC would never fire. stream_user is an account owner with the same
    # role, so RLS exposes the data and RBAC can enforce the expected 403.
    x_user = t.get('stream_user') or f"eval.stream.{t['role']}"
    headers = {'x-role': t['role'], 'x-user': x_user,
               'Accept': 'text/event-stream'}
    payload = {'user_query': t['query'], 'session_id': f'eval-stream-{eval_id}'}
    row = {
        'id': f'{eval_id}s', 'path': '/query/stream',
        'query': t['query'], 'role': t['role'],
        'expected_tools': t.get('expected_tools', []),
        'expect_status': t.get('expect_status'),
        'notes': t.get('notes', '') + ' [stream]',
    }
    try:
        t0 = time.time()
        r = requests.post(f'{BASE_URL}/query/stream', json=payload, headers=headers,
                          timeout=45, stream=True)
        row['latency_ms'] = round((time.time() - t0) * 1000)
        row['status_code'] = r.status_code

        # Parse SSE events
        actual_tools: list = []
        done_event: dict = {}
        error_event: dict = {}
        if r.status_code == 200:
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith('data: '):
                    continue
                try:
                    evt = json.loads(line[6:])
                except Exception:
                    continue
                etype = evt.get('type', '')
                if etype == 'tool_result':
                    tool_name = evt.get('step', {}).get('tool')
                    if tool_name and tool_name not in actual_tools:
                        actual_tools.append(tool_name)
                elif etype == 'done':
                    done_event = evt
                elif etype == 'error':
                    error_event = evt
                    row['status_code'] = evt.get('status', r.status_code)

        elif r.status_code in (400, 403):
            try:
                error_event = r.json()
            except Exception:
                error_event = {'raw': r.text[:200]}

        row['actual_tools'] = actual_tools
        # Stream path: subset match — all expected tools must be present but
        # the ReAct agent may call additional tools for thorough investigation.
        # stream_expected_tools overrides expected_tools when stream behavior legitimately differs.
        expected = t.get('stream_expected_tools', t.get('expected_tools', []))
        row['tool_match'] = all(tool in actual_tools for tool in expected)
        row['status_match'] = row['status_code'] == t.get('expect_status')
        _set_grounded(row, row['status_code'], {'steps': [{'tool': t} for t in actual_tools]})
        row['body'] = {'done': done_event, 'error': error_event}
    except Exception as e:
        _fail_row(row, e)
    return row


def _set_grounded(row: dict, status_code: int, body: dict) -> None:
    """Grounding: response must be based on real tool calls, not hallucinated."""
    if status_code == 200:
        tool_steps = [s for s in body.get('steps', []) if s.get('tool')]
        row['grounded'] = bool(tool_steps)
    elif status_code in (400, 403):
        # 400 = prompt_guard enforced; 403 = RBAC enforced — both are correct, grounded responses.
        row['grounded'] = True
    else:
        row['grounded'] = False


def _fail_row(row: dict, exc: Exception) -> None:
    row['error'] = str(exc)
    row['latency_ms'] = -1
    row['tool_match'] = False
    row['status_match'] = False
    row['grounded'] = False


# ── Run evaluations ───────────────────────────────────────────────────────────
_flush_query_cache()
results = []
for idx, t in enumerate(tests):
    eval_id = t.get('id', f'T{idx+1:02d}')
    if _run_sync:
        results.append(_eval_sync(t, eval_id))
    if _run_stream:
        results.append(_eval_stream(t, eval_id))

summary = {
    'total_tests': len(results),
    'tool_match_count': sum(1 for r in results if r.get('tool_match')),
    'status_match_count': sum(1 for r in results if r.get('status_match')),
    'grounded_count': sum(1 for r in results if r.get('grounded')),
    'total_latency_ms': sum(r.get('latency_ms', 0) for r in results if r.get('latency_ms', 0) > 0),
    'avg_latency_ms': round(
        sum(r.get('latency_ms', 0) for r in results if r.get('latency_ms', 0) > 0)
        / max(1, sum(1 for r in results if r.get('latency_ms', 0) > 0))
    ),
}

# Determine verdict
all_pass = (
    summary['tool_match_count'] >= len(results) - 1  # allow 1 tool-match miss (LLM non-determinism)
    and summary['status_match_count'] == len(results)
    and summary['grounded_count'] == len(results)
)
summary['verdict'] = 'PASS' if all_pass else 'FAIL'

report = {'summary': summary, 'results': results}

os.makedirs('evals/reports', exist_ok=True)
with open('evals/reports/results.json', 'w') as f:
    json.dump(report, f, indent=2, default=str)

# ── Console output ────────────────────────────────────────────────────────────
print(f"\n{'─'*72}")
print(f"  Acme Ops Eval  |  {summary['total_tests']} tests")
print(f"{'─'*72}")
print(f"  {'ID':<5} {'Role':<14} {'Status':>6}  {'Tools':<6}  {'Ground':<6}  {'ms':>5}  Notes")
print(f"{'─'*72}")
for r in results:
    sm = '✓' if r.get('status_match') else '✗'
    tm = '✓' if r.get('tool_match') else '✗'
    gr = '✓' if r.get('grounded') else '✗'
    ms = str(r.get('latency_ms', '?'))
    note = (r.get('notes') or '')[:35]
    print(f"  {r['id']:<5} {r['role']:<14} {sm:>6}  {tm:<6}  {gr:<6}  {ms:>5}  {note}")
print(f"{'─'*72}")
print(
    f"  tool_match: {summary['tool_match_count']}/{summary['total_tests']}  "
    f"status_match: {summary['status_match_count']}/{summary['total_tests']}  "
    f"grounded: {summary['grounded_count']}/{summary['total_tests']}  "
    f"avg_latency: {summary['avg_latency_ms']}ms  "
    f"verdict: {summary['verdict']}"
)
print(f"{'─'*72}\n")
print(f"Full report → evals/reports/results.json")
