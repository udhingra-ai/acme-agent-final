"""
Evaluation harness for Acme Operations Agentic Assistant.

Usage:
    python evals/runner.py

Writes results to evals/reports/results.json.
Expected baseline: 10/10 status_match, ≥9/10 tool_match, 10/10 grounded.
"""
import time
import yaml
import json
import requests
import os

BASE_URL = os.getenv('APP_URL', 'http://localhost:8000')

with open('evals/test_queries.yaml') as f:
    tests = yaml.safe_load(f)

results = []
for idx, t in enumerate(tests):
    eval_id = t.get('id', f'T{idx+1:02d}')
    headers = {'x-role': t['role'], 'x-user': f"eval.{t['role']}"}
    payload = {'user_query': t['query'], 'session_id': f'eval-{eval_id}'}
    row = {
        'id': eval_id,
        'query': t['query'],
        'role': t['role'],
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

        # Grounding: did the agent base its response on actual tool calls (real DB data)?
        # A grounded response invokes at least one tool and returns the result faithfully,
        # even if the DB returned no rows (unknown customer = correctly grounded empty response).
        # A non-grounded response would answer without calling any tools (hallucination).
        # 403 = RBAC enforced correctly; 400 = prompt_guard blocked before any LLM call — both grounded.
        if r.status_code == 200:
            tool_steps = [s for s in body.get('steps', []) if s.get('tool')]
            row['grounded'] = bool(tool_steps)
        elif r.status_code in (400, 403):
            row['grounded'] = True
        else:
            row['grounded'] = False

    except Exception as e:
        row['error'] = str(e)
        row['latency_ms'] = -1
        row['tool_match'] = False
        row['status_match'] = False
        row['grounded'] = False

    results.append(row)

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
