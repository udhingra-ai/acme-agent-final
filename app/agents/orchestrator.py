import uuid
from fastapi import HTTPException
from auth.security import require_role
from services.tools_registry import TOOL_MAP
from services.memory_service import append_session_event
from services.answer_synthesizer import synthesize_answer
from agents.risk_action_agent import run_risk_action_agent, select_primary_issue
from agents.planner import build_plan
from observability.logging_utils import log_event


def run_agent(user_query: str, session_id: str, user_ctx: dict):
    trace_id = str(uuid.uuid4())[:8]

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

    # ── Tool Execution (orchestrator/app layer) ───────────────────────────
    # Tool calls are always dispatched here, never by LLMs directly.
    # RBAC is enforced here before write tools are invoked.
    for planned_step in plan['steps']:
        tool_name = planned_step['tool']

        if tool_name == 'list_all_open_issues':
            args = planned_step.get('args') or {}
            severity = args.get('severity')
            statuses = args.get('statuses')
            all_issues = TOOL_MAP[tool_name](severity=severity, statuses=statuses)
            steps.append({'tool': tool_name, 'args': args, 'output': all_issues})

        elif tool_name == 'get_customer_profile':
            profile = TOOL_MAP[tool_name](customer_name)
            steps.append({'tool': tool_name, 'args': {'customer_name': customer_name}, 'output': profile})

        elif tool_name == 'get_open_issues':
            issues = TOOL_MAP[tool_name](customer_name)
            steps.append({'tool': tool_name, 'args': {'customer_name': customer_name}, 'output': issues})

        elif tool_name == 'get_issue_history':
            if not issues:
                continue
            primary = select_primary_issue(issues)
            issue_history = TOOL_MAP[tool_name](primary['id'])
            steps.append({'tool': tool_name, 'args': {'issue_id': primary['id']}, 'output': issue_history})

        elif tool_name == 'recommend_next_action':
            require_role(user_ctx, ['support_user', 'admin'])
            if not issues:
                raise HTTPException(status_code=400, detail='No issue available for next action')
            primary = select_primary_issue(issues)
            next_action = TOOL_MAP[tool_name](primary['id'], user_ctx['username'])
            steps.append({
                'tool': tool_name,
                'args': {'issue_id': primary['id'], 'owner': user_ctx['username']},
                'output': next_action,
            })

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
