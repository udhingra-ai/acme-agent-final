from fastapi import HTTPException
from auth.security import require_role
from services.tools_registry import TOOL_MAP
from services.memory_service import append_session_event, get_session_context
from services.answer_synthesizer import synthesize_answer
from skills.customer_escalation import customer_escalation_summary
from agents.planner import build_plan


def run_agent(user_query: str, session_id: str, user_ctx: dict):
    plan = build_plan(user_query, user_ctx['roles'])
    customer_name = plan.get('customer_name', '')
    steps = []

    profile = None
    issues = []
    issue_history = []
    next_action = None
    all_issues = []

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
            issue_history = TOOL_MAP[tool_name](issues[0]['id'])
            steps.append({'tool': tool_name, 'args': {'issue_id': issues[0]['id']}, 'output': issue_history})

        elif tool_name == 'recommend_next_action':
            require_role(user_ctx, ['support_user', 'admin'])
            if not issues:
                raise HTTPException(status_code=400, detail='No issue available for next action')
            next_action = TOOL_MAP[tool_name](issues[0]['id'], user_ctx['username'])
            steps.append({'tool': tool_name, 'args': {'issue_id': issues[0]['id'], 'owner': user_ctx['username']}, 'output': next_action})

    # Escalation skill — single-customer only
    skill_output = None
    if issues or profile:
        skill_output = customer_escalation_summary(customer_name, profile or {}, issues, issue_history)
        steps.append({'skill': 'customer_escalation_summary', 'output': skill_output})

    # Try LLM synthesis; fall back to deterministic string building if unavailable
    final = synthesize_answer(user_query, steps, escalation=skill_output, next_action=next_action)

    if not final:
        final = _rule_based_answer(plan, all_issues, profile, issues, issue_history, skill_output, next_action)

    event = {'query': user_query, 'plan': plan, 'steps': steps, 'answer': final, 'auth_mode': user_ctx.get('auth_mode')}
    session_state = append_session_event(session_id, event)
    return {'answer': final, 'plan': plan, 'steps': steps, 'session_context': session_state}


def _rule_based_answer(plan, all_issues, profile, issues, issue_history, skill_output, next_action) -> str:
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

    if skill_output:
        risk = skill_output.get('risk_level', 'Unknown')
        urgency = skill_output.get('urgency', '')
        rationale = skill_output.get('risk_rationale', '')
        missing = ', '.join(skill_output.get('missing_information', []))
        urgency_str = f" — urgency: {urgency}" if urgency else ""
        answer_parts.append(f"Escalation risk: **{risk}**{urgency_str}. {skill_output['executive_summary']}")
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
