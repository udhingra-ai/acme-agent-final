from skills.customer_escalation import customer_escalation_summary
from observability.logging_utils import log_event

_SEVERITY_RANK = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
_STATUS_RANK = {'open': 4, 'in_progress': 3, 'waiting': 2, 'resolved': 1}


def select_primary_issue(issues: list) -> dict | None:
    """
    Deterministic primary-issue selection:
    1. Highest severity (critical > high > medium > low)
    2. Most-active status (open > in_progress > waiting > resolved)
    3. Highest issue id (most recently created) as tiebreaker
    """
    if not issues:
        return None
    return max(
        issues,
        key=lambda i: (
            _SEVERITY_RANK.get((i.get('severity') or 'low').lower(), 0),
            _STATUS_RANK.get((i.get('status') or 'open').lower(), 0),
            i.get('id', 0),
        ),
    )


def run_risk_action_agent(
    customer_name: str,
    profile: dict,
    issues: list,
    issue_history: list,
    trace_id: str = '',
) -> dict:
    """
    Risk/Action Agent — Agent 2.

    Consumes grounded tool outputs (profile, issues, history).
    Produces a structured risk assessment and deterministic primary-issue
    selection. Does not perform writes; write actions remain governed by
    RBAC in the orchestrator/app layer.
    """
    primary_issue = select_primary_issue(issues)
    escalation = customer_escalation_summary(customer_name, profile or {}, issues, issue_history)

    output = {
        'selected_primary_issue': primary_issue,
        'customer_name': customer_name,
        'executive_summary': escalation['executive_summary'],
        'customer_health': escalation['customer_health'],
        'risk_level': escalation['risk_level'],
        'rationale': escalation['risk_rationale'],
        'urgency': escalation['urgency'],
        'recommended_next_action': escalation['recommended_next_action'],
        'owner_suggestion': escalation['owner_suggestion'],
        'missing_information': escalation['missing_information'],
        'evidence_used': escalation['evidence_used'],
    }

    log_event('agent_output', {
        'agent_stage': 'risk_action_agent',
        'trace_id': trace_id,
        'customer_name': customer_name,
        'issues_evaluated': len(issues),
        'primary_issue_id': primary_issue.get('id') if primary_issue else None,
        'primary_issue_severity': (primary_issue.get('severity') or '').upper() if primary_issue else None,
        'risk_level': output['risk_level'],
        'urgency': output['urgency'],
    })

    return output
