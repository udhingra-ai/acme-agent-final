from datetime import datetime, timezone


def customer_escalation_summary(customer_name: str, profile: dict, issues: list, history: list):
    """
    Deterministic risk assessment for a single customer.

    Risk rubric (applied in priority order):
      Critical : any critical-severity issue, OR account health = red
      High     : any high-severity issue, OR amber health + multiple issues
      Medium   : medium-severity issue, OR multiple open issues,
                 OR no history on record, OR last update > 7 days ago
      Low      : only low-severity issues, health green/unknown, single issue

    Escalating factors that raise the floor to Medium:
      - more than one open issue
      - no issue history recorded
      - last history entry is 7+ days old
    """
    severity_rank = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
    health = (profile.get('health_status') or 'unknown').lower()

    max_sev_int = max(
        (severity_rank.get((i.get('severity') or '').lower(), 1) for i in issues),
        default=0
    )

    risk_int = max_sev_int
    rationale_parts = []

    sev_label = {0: 'none', 1: 'Low', 2: 'Medium', 3: 'High', 4: 'Critical'}
    if max_sev_int >= 3:
        rationale_parts.append(f"{sev_label[max_sev_int]}-severity issue present")

    # Account health can push risk up independently of issue severity
    if health == 'red':
        risk_int = max(risk_int, 4)
        rationale_parts.append("account health is red (critical account)")
    elif health == 'amber':
        risk_int = max(risk_int, 2)
        if len(issues) > 1:
            risk_int = max(risk_int, 3)
            rationale_parts.append("amber health with multiple open issues")
        else:
            rationale_parts.append("account health is amber")

    if len(issues) > 1:
        risk_int = max(risk_int, 2)
        if "multiple open issues" not in " ".join(rationale_parts):
            rationale_parts.append(f"{len(issues)} open issues unresolved")

    # Check how stale the last history entry is
    stale = False
    days_stale = 0
    if history:
        try:
            last_ts = history[-1].get('created_at') or history[-1].get('updated_at')
            if last_ts:
                last_dt = last_ts if isinstance(last_ts, datetime) \
                    else datetime.fromisoformat(str(last_ts)[:19])
                days_stale = (datetime.now(timezone.utc) - last_dt.replace(tzinfo=timezone.utc)).days
                if days_stale >= 7:
                    stale = True
                    risk_int = max(risk_int, 2)
                    rationale_parts.append(f"no issue update in {days_stale} days")
        except Exception:
            pass
    else:
        risk_int = max(risk_int, 2)
        rationale_parts.append("no issue history on record")

    # Always assign at least Low when there are open issues
    if issues and risk_int == 0:
        risk_int = 1

    risk_map = {0: 'Low', 1: 'Low', 2: 'Medium', 3: 'High', 4: 'Critical'}
    risk = risk_map[min(risk_int, 4)]

    urgency_map = {'Low': 'routine', 'Medium': 'within 48 h', 'High': 'today', 'Critical': 'immediate'}
    urgency = urgency_map[risk]

    sev_display = sev_label.get(max_sev_int, 'unknown')
    summary = (
        f"{customer_name} has {len(issues)} open issue(s). "
        f"Highest severity: {sev_display}. "
        f"Account health: {health}."
    )

    if risk == 'Critical':
        owner_suggestion = 'Escalate to account executive and support manager immediately.'
    elif risk == 'High':
        owner_suggestion = 'Assign to support manager; loop in account owner.'
    elif risk == 'Medium':
        owner_suggestion = 'Assign to support_user; schedule review within 48 hours.'
    else:
        owner_suggestion = 'Standard queue; no immediate escalation required.'

    if risk == 'Critical':
        rec = (
            'Escalate to account executive immediately. '
            'Validate customer impact within 2 hours, assign dedicated owner, '
            'and send a status update to the customer.'
        )
    elif risk == 'High':
        rec = (
            'Assign owner and validate customer impact today. '
            'Provide a status update within 4 hours.'
        )
    else:
        rec = (
            'Assign an owner, validate current customer impact, '
            'and provide an update within one business day.'
        )

    missing = []
    if not history:
        missing.append('Issue history missing')
    elif stale:
        missing.append(f'Issue update overdue ({days_stale} days since last entry)')
    if any(not i.get('owner') for i in issues):
        missing.append('Issue owner not assigned')
    if not missing:
        missing = ['Confirmed business impact', 'Committed resolution ETA']

    evidence_used = {
        'customer_id': profile.get('id'),
        'issue_ids': [i['id'] for i in issues if i.get('id')],
        'history_events': len(history),
        'sources': (
            ['customers', 'issues']
            + (['issue_updates'] if history else [])
        ),
    }

    return {
        'customer_name': customer_name,
        'executive_summary': summary,
        'customer_health': health,
        'risk_level': risk,
        'risk_rationale': '; '.join(rationale_parts) if rationale_parts else 'no elevated risk signals',
        'urgency': urgency,
        'recommended_next_action': rec,
        'owner_suggestion': owner_suggestion,
        'missing_information': missing,
        'evidence_used': evidence_used,
    }
