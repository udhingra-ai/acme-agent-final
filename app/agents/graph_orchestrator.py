"""
LangGraph-based orchestrator implementing a bounded ReAct loop.

Pipeline (as a StateGraph):

  pre_flight → think → rbac_gate → execute → think (loop)
                    ↘ (done/max_iter)
                      risk_assess → END

Disambiguation: emitted as a 'disambiguation' SSE event before the graph runs
if the customer name matches multiple candidates in the DB.

The 'think' node is the ReAct reasoning step: given accumulated observations,
the LLM (or deterministic fallback) decides the next tool or "done".
RBAC enforcement lives in 'rbac_gate', not the LLM.
"""
import json
import time
import uuid
from typing import TypedDict, Optional, List

from langgraph.graph import StateGraph, END
from fastapi import HTTPException

from auth.security import require_role as _require_role
from services.tools_registry import TOOL_MAP
from agents.risk_action_agent import run_risk_action_agent, select_primary_issue
from services.answer_synthesizer import synthesize_answer_stream
from services.memory_service import append_session_event, get_session_context
from agents.planner import infer_customer_name, build_rule_plan, TOOL_DESCRIPTIONS
from repositories.customer_repo import find_customer_matches
from observability.logging_utils import log_event
from core.config import OPENAI_API_KEY, OPENAI_MODEL

MAX_ITERATIONS = 6

# Write-gated tool registry — each entry carries the allowed roles and an audit label.
# Any new tool that mutates data must be added here; the RBAC gate enforces it automatically.
_WRITE_TOOL_REGISTRY: dict = {
    'recommend_next_action': {
        'roles': ['support_user', 'admin'],
        'audit_label': 'create_next_action',
    },
}
_WRITE_TOOLS = set(_WRITE_TOOL_REGISTRY.keys())
_WRITE_ROLES = ['support_user', 'admin']

# Startup assertion: all registered write tools must exist in TOOL_MAP
from services.tools_registry import TOOL_MAP as _TOOL_MAP_CHECK
_missing = _WRITE_TOOLS - set(_TOOL_MAP_CHECK.keys())
assert not _missing, f'Write tools in registry missing from TOOL_MAP: {_missing}'


# ── State ─────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    query: str
    session_id: str
    user_ctx: dict
    trace_id: str
    iteration: int
    customer_name: str
    confirmed_customer: str          # set by caller when user confirmed disambiguation
    thoughts: List[str]
    profile: Optional[dict]
    issues: List[dict]
    issue_history: List[dict]
    next_action_result: Optional[dict]
    all_issues: List[dict]
    steps: List[dict]
    next_tool: str                   # tool name or "done"
    next_tool_args: dict
    rbac_error: Optional[str]
    risk_output: Optional[dict]
    plan_queue: Optional[List[dict]] # rule-fallback: pre-computed steps to pop from (None = not yet built)
    planner_mode: str
    disambiguation_matches: List[str]


# ── Node helpers ──────────────────────────────────────────────────────────────

def _persist_trace_step(trace_id: str, node: str, delta: dict) -> None:
    """
    Write each node's output to Redis so the full trace is recoverable from any pod.
    Enables horizontal scaling: a new pod can reconstruct what happened if needed.
    Keys expire after 1 hour.
    """
    try:
        from core.redis_client import r
        safe_delta = {k: str(v)[:300] for k, v in delta.items()
                      if k not in ('embedding', 'user_ctx')}
        r.rpush(f'trace:{trace_id}:steps',
                json.dumps({'node': node, 'ts': time.time(), **safe_delta}, default=str))
        r.expire(f'trace:{trace_id}:steps', 3600)
    except Exception:
        pass


def _audit_write(trace_id: str, tool: str, user_ctx: dict, args: dict) -> None:
    """Append an immutable audit record for every write operation."""
    try:
        from core.redis_client import r
        record = {
            'tool': tool,
            'label': _WRITE_TOOL_REGISTRY.get(tool, {}).get('audit_label', tool),
            'user': user_ctx.get('username', ''),
            'roles': user_ctx.get('roles', []),
            'args': {k: str(v)[:100] for k, v in args.items()},
            'ts': time.time(),
        }
        r.rpush(f'audit:writes:{trace_id}', json.dumps(record))
        r.expire(f'audit:writes:{trace_id}', 86400)  # 24-hour audit retention
    except Exception:
        pass


def _build_observation_summary(steps: List[dict]) -> List[str]:
    """Compact per-step summary passed to the LLM think prompt."""
    summaries = []
    for s in steps:
        tool = s.get('tool', s.get('skill', 'unknown'))
        out = s.get('output')
        if isinstance(out, list):
            summaries.append(f'{tool}: {len(out)} rows returned')
        elif isinstance(out, dict) and 'error' not in out:
            keys = list(out.keys())[:5]
            summaries.append(f'{tool}: returned {{{", ".join(keys)}}}')
        else:
            summaries.append(f'{tool}: {str(out)[:80]}')
    return summaries


# ── Nodes ─────────────────────────────────────────────────────────────────────

_PREP_PATTERNS = [
    r'\bwith\s+(\w[\w\s]{1,30})',
    r'\bfor\s+(\w[\w\s]{1,30})',
    r'\babout\s+(\w[\w\s]{1,30})',
    r'\bon\s+(\w[\w\s]{1,30})',
    r'\bregarding\s+(\w[\w\s]{1,30})',
    r'\bcustomer\s+(\w[\w\s]{1,30})',
    r'\bclient\s+(\w[\w\s]{1,30})',
    r'\bof\s+(\w[\w\s]{1,30})',
]
_PREP_STOP = {'all', 'every', 'any', 'each', 'my', 'the', 'our', 'your',
              'this', 'that', 'risk', 'issues', 'issue', 'open', 'latest',
              'critical', 'high', 'medium', 'low'}

import re as _re


def _extract_name_candidate(query: str) -> str:
    """
    Extract a potential customer name from the query, handling both
    capitalised names ("Nexus Payments") and all-lowercase fragments ("nexi", "nexus").
    Returns the first plausible candidate or ''.
    """
    # Try capitalised extraction first (existing logic)
    raw = infer_customer_name(query)
    if raw:
        return raw

    # Fallback: extract lowercase word(s) after prepositions
    for pattern in _PREP_PATTERNS:
        m = _re.search(pattern, query, _re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().rstrip('?.!,;')
            # Take up to 3 words
            words = candidate.split()[:3]
            candidate = ' '.join(words)
            if candidate.lower() not in _PREP_STOP and len(candidate) >= 3:
                return candidate
    return ''


def _pre_flight(state: AgentState) -> dict:
    """
    Resolve the customer name from the query.
    If multiple DB matches exist, return them for disambiguation.
    If the caller already confirmed a name (confirmed_customer), use it directly.
    """
    if state.get('confirmed_customer'):
        return {
            'customer_name': state['confirmed_customer'],
            'disambiguation_matches': [],
        }

    raw = _extract_name_candidate(state['query'])
    if not raw:
        return {'customer_name': '', 'disambiguation_matches': []}

    matches, exact = find_customer_matches(raw)

    if exact and len(matches) == 1:
        # Exact DB match — proceed without asking
        return {'customer_name': matches[0], 'disambiguation_matches': []}
    elif matches:
        # Fuzzy match (single or multiple) — always ask user to confirm
        return {'customer_name': raw, 'disambiguation_matches': matches}
    else:
        return {'customer_name': '', 'disambiguation_matches': []}


def _think(state: AgentState) -> dict:
    """
    ReAct Thought step: decide the next tool to call (or 'done').
    Uses LLM when key is available; falls back to rule-based plan queue.
    """
    # Disambiguation detected — stream handler will surface it and return
    if len(state.get('disambiguation_matches', [])) > 1:
        return {}

    if OPENAI_API_KEY and OPENAI_API_KEY != 'replace_me':
        return _think_llm(state)
    return _think_rule(state)


def _think_llm(state: AgentState) -> dict:
    """LLM-based ReAct reasoning with prior-session context."""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, max_retries=3)

    # Session history — last 2 turns for conversational continuity
    session = get_session_context(state['session_id'])
    prior = session.get('history', [])[-2:]
    prior_summary = '; '.join(
        f"Q: {t.get('query', '')[:60]} → {t.get('answer', '')[:80]}" for t in prior
    ) if prior else 'none'

    # Persistent cross-session memory — user preferences + customer context
    from services.persistent_memory import get_memories_for_context
    memories = get_memories_for_context(
        state['user_ctx'].get('username', ''),
        state.get('customer_name', ''),
    )
    memory_block = '\n'.join(f'  - {m}' for m in memories) if memories else '  none'

    called_tools = [s.get('tool') for s in state.get('steps', []) if s.get('tool')]
    obs = _build_observation_summary(state.get('steps', []))

    system = f"""You are an agentic operations assistant. Decide the NEXT single tool to call, or "done".

Query: {state['query']}
Customer name resolved: {state.get('customer_name', 'none')}
Iteration: {state.get('iteration', 0)} of max {MAX_ITERATIONS}
Prior conversation context: {prior_summary}
Persistent memory (cross-session context — use to inform response):
{memory_block}
Observations so far: {json.dumps(obs)}
Tools already called this turn: {called_tools}

Available tools:
{json.dumps({k: v for k, v in TOOL_DESCRIPTIONS.items()}, indent=2)}

Rules:
1. No named customer → use list_all_open_issues (never call get_customer_profile with empty name)
2. Named customer → get_customer_profile first, then get_open_issues if issues asked, then get_issue_history if history/status/summary asked
3. semantic_search_issues → use for conceptual queries like "find issues similar to X" or "issues mentioning rate limiting"
4. recommend_next_action → only if user explicitly asks to suggest/create/recommend an action
5. Never repeat a tool already called this turn
6. Return "done" when you have enough data to answer the query

Return ONLY valid JSON: {{"thought": "<your reasoning>", "next_tool": "<tool_name or done>", "args": {{}}}}"""

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            response_format={'type': 'json_object'},
            messages=[{'role': 'system', 'content': system}]
        )
        data = json.loads(resp.choices[0].message.content)
        thought = data.get('thought', '')
        next_tool = data.get('next_tool', 'done')
        args = data.get('args') or {}

        # Safety: prevent tool repetition
        if next_tool in called_tools:
            next_tool = 'done'
            thought += f' (skipped — {next_tool} already called)'

        return {
            'next_tool': next_tool,
            'next_tool_args': args,
            'thoughts': state.get('thoughts', []) + [thought],
            'planner_mode': 'react_llm',
            'iteration': state.get('iteration', 0) + 1,
        }
    except Exception:
        return _think_rule(state)


def _think_rule(state: AgentState) -> dict:
    """Deterministic fallback: build plan once, pop steps from queue."""
    queue = state.get('plan_queue')

    if queue is None:
        # First iteration — build the full plan
        plan = build_rule_plan(state['query'], state['user_ctx'].get('roles', []))
        queue = plan.get('steps', [])
        customer_name = plan.get('customer_name', state.get('customer_name', ''))
        if not queue:
            return {
                'next_tool': 'done',
                'thoughts': state.get('thoughts', []) + ['[rule] No tools required.'],
                'plan_queue': [],
                'planner_mode': 'rule_fallback',
                'customer_name': customer_name,
            }
        step = queue[0]
        return {
            'next_tool': step['tool'],
            'next_tool_args': step.get('args') or {},
            'plan_queue': queue[1:],
            'planner_mode': 'rule_fallback',
            'customer_name': customer_name,
            'thoughts': state.get('thoughts', []) + [f'[rule] → {step["tool"]}'],
            'iteration': state.get('iteration', 0) + 1,
        }

    if queue:
        step = queue[0]
        return {
            'next_tool': step['tool'],
            'next_tool_args': step.get('args') or {},
            'plan_queue': queue[1:],
            'thoughts': state.get('thoughts', []) + [f'[rule] → {step["tool"]}'],
            'iteration': state.get('iteration', 0) + 1,
        }

    return {
        'next_tool': 'done',
        'thoughts': state.get('thoughts', []) + ['[rule] All planned tools executed.'],
    }


def _rbac_gate(state: AgentState) -> dict:
    """Enforce RBAC before write tools execute. Uses registry so new write tools are auto-gated."""
    tool = state.get('next_tool', '')
    if tool in _WRITE_TOOLS:
        allowed_roles = _WRITE_TOOL_REGISTRY[tool]['roles']
        roles = state['user_ctx'].get('roles', [])
        if not any(r in allowed_roles for r in roles):
            return {'rbac_error': f"Tool '{tool}' requires {allowed_roles}. Current roles: {roles}"}
    return {'rbac_error': None}


def _execute(state: AgentState) -> dict:
    """Execute the tool decided by the think node. Append result to steps."""
    tool = state.get('next_tool', '')
    args = state.get('next_tool_args') or {}
    customer_name = state.get('customer_name', '')

    new_steps = list(state.get('steps', []))
    new_profile = state.get('profile')
    new_issues = list(state.get('issues', []))
    new_history = list(state.get('issue_history', []))
    new_next_action = state.get('next_action_result')
    new_all_issues = list(state.get('all_issues', []))

    user_ctx = state['user_ctx']

    try:
        if tool == 'list_all_open_issues':
            result = TOOL_MAP[tool](severity=args.get('severity'),
                                    statuses=args.get('statuses'),
                                    user_ctx=user_ctx)
            new_all_issues = result
            new_steps.append({'tool': tool, 'args': args, 'output': result})

        elif tool == 'get_customer_profile':
            result = TOOL_MAP[tool](customer_name)
            new_profile = result
            new_steps.append({'tool': tool, 'args': {'customer_name': customer_name}, 'output': result})

        elif tool == 'get_open_issues':
            result = TOOL_MAP[tool](customer_name, user_ctx=user_ctx)
            new_issues = result
            new_steps.append({'tool': tool, 'args': {'customer_name': customer_name}, 'output': result})

        elif tool == 'get_issue_history':
            issues_now = new_issues or state.get('issues', [])
            if issues_now:
                primary = select_primary_issue(issues_now)
                result = TOOL_MAP[tool](primary['id'])
                new_history = result
                new_steps.append({'tool': tool, 'args': {'issue_id': primary['id']}, 'output': result})

        elif tool == 'recommend_next_action':
            issues_now = new_issues or state.get('issues', [])
            if issues_now:
                primary = select_primary_issue(issues_now)
                write_args = {'issue_id': primary['id'], 'owner': user_ctx['username']}
                _audit_write(state['trace_id'], tool, user_ctx, write_args)
                result = TOOL_MAP[tool](primary['id'], user_ctx['username'])
                new_next_action = result
                new_steps.append({
                    'tool': tool,
                    'args': write_args,
                    'output': result,
                })

        elif tool == 'semantic_search_issues':
            result = TOOL_MAP[tool](args.get('query', state['query']), user_ctx=user_ctx)
            new_steps.append({'tool': tool, 'args': args, 'output': result})

    except Exception as exc:
        new_steps.append({'tool': tool, 'args': args, 'output': {'error': str(exc)}})

    log_event('tool_call', {
        'tool': tool,
        'trace_id': state['trace_id'],
        'iteration': state.get('iteration', 0),
        'via': 'graph_orchestrator',
    })

    return {
        'steps': new_steps,
        'profile': new_profile,
        'issues': new_issues,
        'issue_history': new_history,
        'next_action_result': new_next_action,
        'all_issues': new_all_issues,
    }


def _risk_assess(state: AgentState) -> dict:
    """Deterministic Risk/Action Agent — runs after all tools complete."""
    if not state.get('issues') and not state.get('profile'):
        return {'risk_output': None}

    risk = run_risk_action_agent(
        state.get('customer_name', ''),
        state.get('profile') or {},
        state.get('issues', []),
        state.get('issue_history', []),
        trace_id=state['trace_id'],
    )
    ra_step = {'skill': 'risk_action_agent', 'output': risk}
    return {
        'risk_output': risk,
        'steps': state.get('steps', []) + [ra_step],
    }


# ── Routing conditions ─────────────────────────────────────────────────────────

def _after_think(state: AgentState) -> str:
    if len(state.get('disambiguation_matches', [])) > 1:
        return 'end'
    if state.get('rbac_error'):
        return 'end'
    nt = state.get('next_tool', 'done')
    if nt == 'done' or state.get('iteration', 0) >= MAX_ITERATIONS:
        return 'risk_assess'
    return 'rbac_gate'


def _after_rbac(state: AgentState) -> str:
    return 'end' if state.get('rbac_error') else 'execute'


# ── Build and compile the graph ────────────────────────────────────────────────

def _build_graph():
    g = StateGraph(AgentState)
    g.add_node('pre_flight', _pre_flight)
    g.add_node('think',      _think)
    g.add_node('rbac_gate',  _rbac_gate)
    g.add_node('execute',    _execute)
    g.add_node('risk_assess', _risk_assess)

    g.set_entry_point('pre_flight')
    g.add_edge('pre_flight', 'think')
    g.add_conditional_edges('think', _after_think, {
        'rbac_gate':  'rbac_gate',
        'risk_assess': 'risk_assess',
        'end':         END,
    })
    g.add_conditional_edges('rbac_gate', _after_rbac, {
        'execute': 'execute',
        'end':     END,
    })
    g.add_edge('execute', 'think')
    g.add_edge('risk_assess', END)
    return g.compile()


_compiled = _build_graph()


# ── Public streaming interface ────────────────────────────────────────────────

def _make_plan_summary(state: AgentState) -> dict:
    return {
        'customer_name': state.get('customer_name', ''),
        'reasoning': ' → '.join(state.get('thoughts', [])) or 'ReAct loop completed.',
        'steps': [{'tool': s.get('tool', s.get('skill', ''))} for s in state.get('steps', [])],
        'planner_mode': state.get('planner_mode', 'react_llm'),
        'roles_seen': state.get('user_ctx', {}).get('roles', []),
    }


def run_agent_stream(user_query: str, session_id: str, user_ctx: dict,
                     confirmed_customer: str = '', trace_id: str = ''):
    """
    Streaming entry point. Yields SSE events:
      disambiguation  — multiple customer name matches; caller should re-send with confirmed_customer
      react_thought   — one per ReAct think iteration (thought + next_tool)
      tool_result     — one per tool execution
      risk_action     — Risk/Action agent output
      token           — LLM response token (streamed)
      answer          — rule-based fallback answer (non-streaming)
      error           — RBAC or execution error
      done            — final event
    """
    # Pre-flight: prompt injection guard — reject before any LLM call or DB access
    from services.prompt_guard import check_prompt
    try:
        check_prompt(user_query)
    except HTTPException as e:
        yield f'data: {json.dumps({"type": "error", "status": e.status_code, "detail": e.detail})}\n\n'
        return

    # Use trace_id threaded from HTTP middleware if provided, otherwise generate one
    trace_id = trace_id or str(uuid.uuid4())[:8]
    roles = user_ctx.get('roles', [])

    # ── Query cache check (Layer 1 exact, Layer 2 semantic) ───────────────────
    if not confirmed_customer:  # skip cache when user already disambiguated (fresh intent)
        from services.query_cache import lookup as cache_lookup
        cache_hit = cache_lookup(user_query, roles, confirmed_customer or '')
        if cache_hit:
            cached_plan = cache_hit.get('plan', {})
            cached_plan['cache_hit'] = True
            yield f'data: {json.dumps({"type": "planning", "plan": cached_plan, "trace_id": trace_id, "cache_hit": True}, default=str)}\n\n'
            yield f'data: {json.dumps({"type": "answer", "text": cache_hit["answer"]})}\n\n'
            yield f'data: {json.dumps({"type": "done", "trace_id": trace_id, "cache_hit": True, "user": {"username": user_ctx["username"], "roles": roles, "auth_mode": user_ctx["auth_mode"]}})}\n\n'
            return

    initial: AgentState = {
        'query': user_query,
        'session_id': session_id,
        'user_ctx': user_ctx,
        'trace_id': trace_id,
        'iteration': 0,
        'customer_name': '',
        'confirmed_customer': confirmed_customer,
        'thoughts': [],
        'profile': None,
        'issues': [],
        'issue_history': [],
        'next_action_result': None,
        'all_issues': [],
        'steps': [],
        'next_tool': '',
        'next_tool_args': {},
        'rbac_error': None,
        'risk_output': None,
        'plan_queue': None,
        'planner_mode': 'react_llm',
        'disambiguation_matches': [],
    }

    accumulated = dict(initial)

    for chunk in _compiled.stream(initial, stream_mode='updates'):
        for node_name, delta in chunk.items():
            accumulated.update(delta)
            _persist_trace_step(trace_id, node_name, delta)

            if node_name == 'pre_flight':
                matches = delta.get('disambiguation_matches', [])
                if len(matches) >= 1:
                    yield f'data: {json.dumps({"type": "disambiguation", "matches": matches, "original_query": user_query})}\n\n'
                    return

            elif node_name == 'think':
                thoughts = delta.get('thoughts', [])
                next_tool = delta.get('next_tool', '')
                if thoughts:
                    yield f'data: {json.dumps({"type": "react_thought", "thought": thoughts[-1], "next_tool": next_tool, "iteration": accumulated.get("iteration", 0)})}\n\n'

            elif node_name == 'rbac_gate':
                err = delta.get('rbac_error')
                if err:
                    yield f'data: {json.dumps({"type": "error", "status": 403, "detail": err})}\n\n'
                    return

            elif node_name == 'execute':
                steps = delta.get('steps', [])
                if steps:
                    step = steps[-1]
                    if step.get('tool'):
                        yield f'data: {json.dumps({"type": "tool_result", "step": step}, default=str)}\n\n'

            elif node_name == 'risk_assess':
                risk = delta.get('risk_output')
                if risk:
                    steps = delta.get('steps', [])
                    ra_step = steps[-1] if steps else {'skill': 'risk_action_agent', 'output': risk}
                    yield f'data: {json.dumps({"type": "risk_action", "step": ra_step}, default=str)}\n\n'

    # Emit planning summary after the loop (all thoughts + tool list known)
    plan_summary = _make_plan_summary(accumulated)
    log_event('agent_output', {
        'agent_stage': 'graph_orchestrator',
        'trace_id': trace_id,
        'planner_mode': plan_summary['planner_mode'],
        'customer_name': plan_summary['customer_name'],
        'total_iterations': accumulated.get('iteration', 0),
        'tools_called': [s.get('tool') for s in accumulated.get('steps', []) if s.get('tool')],
        'role': user_ctx.get('roles', []),
    })
    yield f'data: {json.dumps({"type": "planning", "plan": plan_summary, "trace_id": trace_id}, default=str)}\n\n'

    # ── Agent 3: Response — stream tokens ─────────────────────────────────────
    full_answer = ''
    for token_event in synthesize_answer_stream(
        user_query,
        accumulated.get('steps', []),
        escalation=accumulated.get('risk_output'),
        next_action=accumulated.get('next_action_result'),
        trace_id=trace_id,
    ):
        yield token_event
        try:
            d = json.loads(token_event[6:])
            if d.get('type') == 'token':
                full_answer += d.get('delta', '')
        except Exception:
            pass

    if not full_answer:
        from agents.orchestrator import _rule_based_answer
        full_answer = _rule_based_answer(
            plan_summary,
            accumulated.get('all_issues', []),
            accumulated.get('profile'),
            accumulated.get('issues', []),
            accumulated.get('issue_history', []),
            accumulated.get('risk_output'),
            accumulated.get('next_action_result'),
        )
        yield f'data: {json.dumps({"type": "answer", "text": full_answer})}\n\n'

    append_session_event(session_id, {
        'query': user_query,
        'plan': plan_summary,
        'steps': accumulated.get('steps', []),
        'answer': full_answer,
        'auth_mode': user_ctx.get('auth_mode'),
        'trace_id': trace_id,
    })

    # ── Post-run: cache response + extract persistent memories (background) ──
    if full_answer:
        from services.query_cache import store as cache_store
        # Use '' for customer so key matches lookup (confirmed_customer is empty at lookup time)
        cache_store(user_query, roles, '', full_answer, plan_summary)

        from services.persistent_memory import extract_and_store_async
        extract_and_store_async(
            user_query, full_answer,
            user_ctx.get('username', ''),
            accumulated.get('customer_name', ''),
        )

    yield f'data: {json.dumps({"type": "done", "trace_id": trace_id, "user": {"username": user_ctx["username"], "roles": user_ctx["roles"], "auth_mode": user_ctx["auth_mode"]}})}\n\n'
