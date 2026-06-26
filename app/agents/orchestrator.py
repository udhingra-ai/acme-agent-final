import json
import uuid
from fastapi import HTTPException
from auth.security import require_role
from services.tools_registry import TOOL_MAP
from agents.graph_orchestrator import _WRITE_TOOL_REGISTRY  # single source of truth for write-tool roles
from services.memory_service import append_session_event
from services.answer_synthesizer import synthesize_answer, synthesize_answer_stream
from agents.risk_action_agent import run_risk_action_agent, select_primary_issue
from agents.planner import build_plan
from observability.logging_utils import log_event


def run_agent(user_query: str, session_id: str, user_ctx: dict, trace_id: str = ''):
    # Prompt injection guard — same check as the streaming path
    from services.prompt_guard import check_prompt
    check_prompt(user_query)

    # Reuse the trace_id threaded from TraceMiddleware (set in routes.py) so
    # the X-Trace-Id response header, request_trace log, and agent logs all
    # share one UUID per request instead of generating a second short UUID here.
    if not trace_id:
        trace_id = str(uuid.uuid4())[:8]
    else:
        trace_id = trace_id[:8]

    # ── Agent 1: Planning Agent ───────────────────────────────────────────
    plan = build_plan(user_query, user_ctx['roles'])
    log_event('agent_output', {
        'agent_stage': 'planning_agent',
        'trace_id': trace_id,
        'planner_mode': plan.get('planner_mode'),
        'customer_name': plan.get('customer_name', ''),
        'selected_tools': [s.get('tool') for s in plan.get('steps', [])],
        'reasoning': plan.get('reasoning', ''),
        'role': user_ctx.get('roles', []),
        'auth_mode': user_ctx.get('auth_mode'),
    })

    customer_name = plan.get('customer_name', '')
    steps = []

    profile = None
    issues = []
    issue_history = []
    next_action = None
    all_issues = []
    search_resolved = False  # True only when search_customers resolved exactly 1 match

    # ── Tool Execution (orchestrator/app layer) ───────────────────────────
    # Tool calls are always dispatched here, never by LLMs directly.
    # RBAC is enforced here before write tools are invoked.
    for planned_step in plan['steps']:
        tool_name = planned_step['tool']

        if tool_name == 'search_customers':
            args = planned_step.get('args') or {}
            result = TOOL_MAP[tool_name](args.get('query', customer_name))
            steps.append({'tool': tool_name, 'args': args, 'output': result})
            # If exactly 1 match found, resolve customer_name for follow-up tools below
            if result.get('count') == 1:
                customer_name = result['matches'][0]
                search_resolved = True

        elif tool_name == 'list_all_open_issues':
            args = planned_step.get('args') or {}
            severity = args.get('severity')
            statuses = args.get('statuses')
            all_issues = TOOL_MAP[tool_name](severity=severity, statuses=statuses, user_ctx=user_ctx)
            steps.append({'tool': tool_name, 'args': args, 'output': all_issues})

        elif tool_name == 'get_customer_profile':
            profile = TOOL_MAP[tool_name](customer_name)
            steps.append({'tool': tool_name, 'args': {'customer_name': customer_name}, 'output': profile})

        elif tool_name == 'get_open_issues':
            raw = TOOL_MAP[tool_name](customer_name, user_ctx=user_ctx)
            rls_restricted = (len(raw) == 1 and raw[0].get('__rls_restricted__')) if raw else False
            if rls_restricted:
                owner = raw[0].get('account_owner', 'another account owner')
                issues = []
                steps.append({'tool': tool_name, 'args': {'customer_name': customer_name}, 'output': [],
                               'rls_note': f"Issue access restricted: {customer_name} is assigned to {owner}. Your account only has read access to your own customers' issues."})
            else:
                issues = raw
                steps.append({'tool': tool_name, 'args': {'customer_name': customer_name}, 'output': issues})

        elif tool_name == 'get_issue_history':
            if not issues:
                continue
            primary = select_primary_issue(issues)
            issue_history = TOOL_MAP[tool_name](primary['id'])
            steps.append({'tool': tool_name, 'args': {'issue_id': primary['id']}, 'output': issue_history})

        elif tool_name == 'recommend_next_action':
            require_role(user_ctx, _WRITE_TOOL_REGISTRY['recommend_next_action']['roles'])
            if not issues:
                raise HTTPException(status_code=400, detail='No issue available for next action')
            primary = select_primary_issue(issues)
            next_action = TOOL_MAP[tool_name](primary['id'], user_ctx['username'])
            steps.append({
                'tool': tool_name,
                'args': {'issue_id': primary['id'], 'owner': user_ctx['username']},
                'output': next_action,
            })

        elif tool_name == 'update_issue_status':
            require_role(user_ctx, _WRITE_TOOL_REGISTRY['update_issue_status']['roles'])
            if not issues:
                raise HTTPException(status_code=400, detail='No issue available to update')
            args = planned_step.get('args') or {}
            primary = select_primary_issue(issues)
            new_status = args.get('new_status', 'in_progress')
            result = TOOL_MAP[tool_name](primary['id'], new_status, user_ctx['username'])
            steps.append({'tool': tool_name,
                          'args': {'issue_id': primary['id'], 'new_status': new_status},
                          'output': result})

        elif tool_name == 'semantic_search_issues':
            args = planned_step.get('args') or {}
            result = TOOL_MAP[tool_name](args.get('query', user_query), user_ctx=user_ctx)
            steps.append({'tool': tool_name, 'args': args, 'output': result})

    # ── Post-search follow-up ─────────────────────────────────────────────
    # When search_customers resolved exactly 1 match but no profile was fetched yet,
    # automatically fetch profile + issues for the resolved customer.
    if search_resolved and profile is None and not all_issues:
        profile = TOOL_MAP['get_customer_profile'](customer_name)
        steps.append({'tool': 'get_customer_profile', 'args': {'customer_name': customer_name}, 'output': profile})
        raw = TOOL_MAP['get_open_issues'](customer_name, user_ctx=user_ctx)
        rls_restricted = (len(raw) == 1 and raw[0].get('__rls_restricted__')) if raw else False
        if rls_restricted:
            owner = raw[0].get('account_owner', 'another account owner')
            issues = []
            steps.append({'tool': 'get_open_issues', 'args': {'customer_name': customer_name}, 'output': [],
                           'rls_note': f"Issue access restricted: {customer_name} is assigned to {owner}. Your account only has read access to your own customers' issues."})
        else:
            issues = raw
            steps.append({'tool': 'get_open_issues', 'args': {'customer_name': customer_name}, 'output': issues})

    # ── Agent 2: Risk/Action Agent (single-customer only) ─────────────────
    # Runs when we have grounded customer data. Produces deterministic risk
    # assessment and explicit primary-issue selection. Does not write.
    risk_action_output = None
    if issues or profile:
        risk_action_output = run_risk_action_agent(
            customer_name, profile or {}, issues, issue_history, trace_id=trace_id
        )
        steps.append({'skill': 'risk_action_agent', 'output': risk_action_output})

    # ── Agent 3: Response Agent ────────────────────────────────────────────
    # Consumes grounded tool outputs + Risk/Action Agent structured output.
    # Produces the final user-facing answer. Falls back to deterministic
    # rule-based synthesis if the LLM is unavailable.
    final = synthesize_answer(
        user_query, steps,
        escalation=risk_action_output,
        next_action=next_action,
        trace_id=trace_id,
    )

    if not final:
        final = _rule_based_answer(plan, all_issues, profile, issues, issue_history, risk_action_output, next_action)

    # Prepend RLS access warning to the answer so users see it regardless of synthesizer path
    rls_note = next((s['rls_note'] for s in steps if s.get('rls_note')), None)
    if rls_note:
        final = f"⚠️ {rls_note}\n\n{final}"

    event = {
        'query': user_query,
        'plan': plan,
        'steps': steps,
        'answer': final,
        'auth_mode': user_ctx.get('auth_mode'),
        'trace_id': trace_id,
    }
    session_state = append_session_event(session_id, event)
    return {
        'answer': final,
        'plan': plan,
        'steps': steps,
        'session_context': session_state,
        'trace_id': trace_id,
    }


def _rule_based_answer(plan, all_issues, profile, issues, issue_history, risk_action_output, next_action) -> str:
    """Deterministic fallback when LLM synthesizer is unavailable."""
    answer_parts = []

    if all_issues:
        by_customer: dict = {}
        for iss in all_issues:
            by_customer.setdefault(iss['customer_name'], []).append(iss)

        first_args = (plan['steps'][0].get('args') or {}) if plan.get('steps') else {}
        severity_label = first_args.get('severity')
        status_labels = first_args.get('statuses')
        qualifier = ''
        if severity_label:
            qualifier += f'**{severity_label.upper()}** '
        if status_labels:
            qualifier += '(' + ' + '.join(s.replace('_', ' ') for s in status_labels) + ') '
        answer_parts.append(f"{qualifier}issues across all clients — {len(all_issues)} total")

        for cname in sorted(by_customer):
            cissues = by_customer[cname]
            lines = [f"  • [{i['severity'].upper()}] [{i['status']}] {i['title']}" for i in cissues]
            answer_parts.append(f"**{cname}** ({len(cissues)} issue{'s' if len(cissues) != 1 else ''}):\n" + "\n".join(lines))

    if profile:
        health = profile.get('health_status', 'unknown')
        segment = profile.get('segment', 'unknown')
        answer_parts.append(f"**{profile['name']}** — Segment: {segment} | Account health: {health}")

    if issues:
        issue_lines = [f"• [{i.get('severity','?').upper()}] {i.get('title','Untitled')} (#{i.get('id')})" for i in issues]
        answer_parts.append(f"Open issues ({len(issues)}):\n" + "\n".join(issue_lines))

    if issue_history:
        latest = issue_history[-1]
        ts = str(latest.get('created_at') or '')[:10]
        note = latest.get('update_text') or '—'
        by = latest.get('updated_by', '')
        answer_parts.append(f"Latest update on #{issues[0]['id'] if issues else '?'} ({ts}, {by}): \"{note}\"")

    if risk_action_output:
        risk = risk_action_output.get('risk_level', 'Unknown')
        urgency = risk_action_output.get('urgency', '')
        rationale = risk_action_output.get('rationale', '')
        missing = ', '.join(risk_action_output.get('missing_information', []))
        urgency_str = f" — urgency: {urgency}" if urgency else ""
        answer_parts.append(f"Escalation risk: **{risk}**{urgency_str}. {risk_action_output['executive_summary']}")
        if rationale:
            answer_parts.append(f"Risk rationale: {rationale}.")
        if missing:
            answer_parts.append(f"Information gaps: {missing}.")

    if next_action:
        answer_parts.append(
            f"Next action created — Owner: {next_action['owner']} | Status: {next_action['status']} | "
            f"Action: {next_action.get('action_text', 'See database for details')}"
        )

    return '\n\n'.join(answer_parts) if answer_parts else 'No relevant information found.'


def run_agent_stream(user_query: str, session_id: str, user_ctx: dict):
    """
    Streaming version of run_agent.
    Yields SSE events so the client can show progressive agent stages and streamed tokens.

    Event types:
      planning     — Planning Agent output; includes plan + trace_id
      tool_result  — one event per tool call as each completes
      risk_action  — Risk/Action Agent structured output
      token        — one delta string from the streaming LLM response
      answer       — full answer text (only emitted when LLM is unavailable; rule-based fallback)
      error        — HTTP error mid-stream (e.g. 403 on write tool)
      done         — final event; includes trace_id and user context
    """
    trace_id = str(uuid.uuid4())[:8]

    # ── Agent 1: Planning ─────────────────────────────────────────────────
    try:
        plan = build_plan(user_query, user_ctx['roles'])
    except Exception as exc:
        yield f'data: {json.dumps({"type": "error", "status": 500, "detail": str(exc)})}\n\n'
        return

    customer_name = plan.get('customer_name', '')
    log_event('agent_output', {
        'agent_stage': 'planning_agent',
        'trace_id': trace_id,
        'planner_mode': plan.get('planner_mode'),
        'customer_name': customer_name,
        'selected_tools': [s.get('tool') for s in plan.get('steps', [])],
        'role': user_ctx.get('roles', []),
        'auth_mode': user_ctx.get('auth_mode'),
    })
    yield f'data: {json.dumps({"type": "planning", "plan": plan, "trace_id": trace_id}, default=str)}\n\n'

    steps = []
    profile = None
    issues = []
    issue_history = []
    next_action = None
    all_issues = []

    # ── Tool Execution ────────────────────────────────────────────────────
    for planned_step in plan['steps']:
        tool_name = planned_step['tool']
        step = None

        try:
            if tool_name == 'list_all_open_issues':
                args = planned_step.get('args') or {}
                all_issues = TOOL_MAP[tool_name](severity=args.get('severity'), statuses=args.get('statuses'))
                step = {'tool': tool_name, 'args': args, 'output': all_issues}

            elif tool_name == 'get_customer_profile':
                profile = TOOL_MAP[tool_name](customer_name)
                step = {'tool': tool_name, 'args': {'customer_name': customer_name}, 'output': profile}

            elif tool_name == 'get_open_issues':
                issues = TOOL_MAP[tool_name](customer_name)
                step = {'tool': tool_name, 'args': {'customer_name': customer_name}, 'output': issues}

            elif tool_name == 'get_issue_history':
                if issues:
                    primary = select_primary_issue(issues)
                    issue_history = TOOL_MAP[tool_name](primary['id'])
                    step = {'tool': tool_name, 'args': {'issue_id': primary['id']}, 'output': issue_history}

            elif tool_name == 'recommend_next_action':
                require_role(user_ctx, _WRITE_TOOL_REGISTRY['recommend_next_action']['roles'])
                if not issues:
                    raise HTTPException(status_code=400, detail='No issue available for next action')
                primary = select_primary_issue(issues)
                next_action = TOOL_MAP[tool_name](primary['id'], user_ctx['username'])
                step = {
                    'tool': tool_name,
                    'args': {'issue_id': primary['id'], 'owner': user_ctx['username']},
                    'output': next_action,
                }

        except HTTPException as exc:
            yield f'data: {json.dumps({"type": "error", "status": exc.status_code, "detail": exc.detail})}\n\n'
            return

        if step:
            steps.append(step)
            yield f'data: {json.dumps({"type": "tool_result", "step": step}, default=str)}\n\n'

    # ── Agent 2: Risk/Action ──────────────────────────────────────────────
    risk_action_output = None
    if issues or profile:
        risk_action_output = run_risk_action_agent(
            customer_name, profile or {}, issues, issue_history, trace_id=trace_id
        )
        ra_step = {'skill': 'risk_action_agent', 'output': risk_action_output}
        steps.append(ra_step)
        yield f'data: {json.dumps({"type": "risk_action", "step": ra_step}, default=str)}\n\n'

    # ── Agent 3: Response — stream tokens ─────────────────────────────────
    full_answer = ''
    for token_event in synthesize_answer_stream(
        user_query, steps,
        escalation=risk_action_output,
        next_action=next_action,
        trace_id=trace_id,
    ):
        yield token_event
        try:
            d = json.loads(token_event[6:])  # strip 'data: '
            if d.get('type') == 'token':
                full_answer += d.get('delta', '')
        except Exception:
            pass

    if not full_answer:
        full_answer = _rule_based_answer(
            plan, all_issues, profile, issues, issue_history, risk_action_output, next_action
        )
        yield f'data: {json.dumps({"type": "answer", "text": full_answer})}\n\n'

    # Persist to Redis session
    append_session_event(session_id, {
        'query': user_query, 'plan': plan, 'steps': steps,
        'answer': full_answer, 'auth_mode': user_ctx.get('auth_mode'), 'trace_id': trace_id,
    })

    yield f'data: {json.dumps({"type": "done", "trace_id": trace_id, "user": {"username": user_ctx["username"], "roles": user_ctx["roles"], "auth_mode": user_ctx["auth_mode"]}})}\n\n'
