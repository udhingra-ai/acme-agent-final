"""
Autonomous agentic behaviors — three modes running without user prompts.

  health_sweep    Scans red/amber customers every 15 min → risk briefing
  escalation      Triggered by CDC when a critical issue gets a new note
  churn_signal    Nightly: detects health deterioration (green→amber, amber→red)

Safety model — what the autonomous agent CAN and CANNOT do:

  CAN:   Write to `briefings` table (surfaced in UI for human review).
         Briefings are informational records, never customer-visible actions.

  CANNOT: Write to `next_actions` table. recommend_next_action is a user-facing
          write tool gated by RBAC (support_user/admin only) and requires an
          explicit user prompt — it is NOT called by any autonomous code path.

  CANNOT: Modify customer data, issue status, or any table outside briefings /
          health_snapshots (the latter is a read-model for churn detection only).

This intentional containment means a bug in autonomous sweep code cannot
create customer-visible actions or escalations without human confirmation.
Account owners acknowledge briefings explicitly via POST /briefings/{id}/acknowledge.
"""
import threading
import time
from observability.logging_utils import log_event


def _try_acquire_lock(lock_name: str, ttl_seconds: int) -> bool:
    """
    Acquire a Redis distributed lock using SET NX EX.
    Returns True (and holds the lock) or False (another pod already holds it).
    Falls back to True (always run) if Redis is unavailable — safe because
    health_sweep and churn_signal are idempotent by design.
    """
    try:
        import redis as redis_lib
        from core.config import REDIS_URL
        if not REDIS_URL:
            return True
        r = redis_lib.from_url(REDIS_URL, socket_connect_timeout=2)
        return bool(r.set(lock_name, '1', nx=True, ex=ttl_seconds))
    except Exception:
        return True  # Redis unavailable — fall through and run; worst case: duplicate briefings


def run_health_sweep() -> int:
    """
    Scan all at-risk customers, run Risk/Action agent for each,
    and store a briefing. Returns the number of new briefings stored.
    """
    stored = 0
    try:
        from repositories.customer_repo import list_all_customers
        from repositories.issue_repo import get_open_issues_for_at_risk_customers
        from agents.risk_action_agent import run_risk_action_agent
        from repositories.briefing_repo import store_briefing

        customers = list_all_customers()
        # Single batch query replaces N+1 per-customer queries at scale
        issues_by_customer = get_open_issues_for_at_risk_customers()

        for c in customers:
            if c['health_status'] not in ('red', 'amber'):
                continue
            issues = issues_by_customer.get(c['name'], [])
            if not issues:
                continue

            risk = run_risk_action_agent(
                c['name'], c, issues, [],
                trace_id=f'sweep-{c["id"]}'
            )
            briefing_id = store_briefing({
                'customer_name':    c['name'],
                'account_owner':    c.get('account_owner', ''),
                'health_status':    c['health_status'],
                'open_issues':      len(issues),
                'risk_level':       risk.get('risk_level', 'unknown'),
                'risk_summary':     risk.get('executive_summary', ''),
                'recommended_action': risk.get('recommended_next_action', ''),
                'urgency':          risk.get('urgency', ''),
                'source':           'health_sweep',
            })
            if briefing_id:
                stored += 1

        log_event('autonomous', {'action': 'health_sweep', 'new_briefings': stored})
    except Exception as exc:
        log_event('autonomous_error', {'action': 'health_sweep', 'error': str(exc)})
    return stored


def check_issue_escalation(issue_id: int | None) -> None:
    """
    CDC-triggered: called when a new note is added to an issue.
    If the issue is critical/high and open, generate an escalation briefing.
    """
    if not issue_id:
        return
    try:
        from sqlalchemy import text
        from core.db import SessionLocal
        from repositories.issue_repo import get_open_issues_for_customer
        from agents.risk_action_agent import run_risk_action_agent
        from repositories.briefing_repo import store_briefing

        with SessionLocal() as db:
            row = db.execute(text('''
                SELECT i.id, i.title, i.severity, i.status,
                       c.name AS customer_name, c.health_status,
                       c.account_owner, c.segment, c.id AS customer_id
                FROM issues i JOIN customers c ON i.customer_id = c.id
                WHERE i.id = :id
            '''), {'id': issue_id}).mappings().first()

        if not row:
            return
        if row['status'].lower() not in ('open', 'in_progress'):
            return
        if row['severity'].lower() not in ('critical', 'high'):
            return

        issues = get_open_issues_for_customer(row['customer_name'])
        customer_ctx = {
            'name': row['customer_name'],
            'health_status': row['health_status'],
            'account_owner': row['account_owner'],
            'segment': row['segment'],
        }
        risk = run_risk_action_agent(
            row['customer_name'], customer_ctx, issues, [],
            trace_id=f'esc-{issue_id}'
        )
        store_briefing({
            'customer_name':    row['customer_name'],
            'account_owner':    row['account_owner'],
            'health_status':    row['health_status'],
            'open_issues':      len(issues),
            'risk_level':       risk.get('risk_level', 'high'),
            'risk_summary':     f"New note on {row['severity'].upper()} issue: \"{row['title']}\". {risk.get('executive_summary', '')}",
            'recommended_action': risk.get('recommended_next_action', ''),
            'urgency':          risk.get('urgency', 'high'),
            'source':           'escalation_cdc',
            'trigger_issue_id': issue_id,
        })
        log_event('autonomous', {
            'action': 'escalation',
            'issue_id': issue_id,
            'customer': row['customer_name'],
        })
    except Exception as exc:
        log_event('autonomous_error', {'action': 'escalation', 'issue_id': issue_id, 'error': str(exc)})


def run_churn_signal() -> int:
    """
    Detect customers whose health deteriorated since the last snapshot.
    Generates a churn-risk briefing for each transition.
    """
    flagged = 0
    try:
        from repositories.customer_repo import list_all_customers
        from repositories.briefing_repo import (
            store_briefing, get_last_health_snapshot, store_health_snapshot
        )

        customers = list_all_customers()
        for c in customers:
            current = c['health_status']
            previous = get_last_health_snapshot(c['name'])

            deteriorated = (
                previous is not None and (
                    (previous == 'green' and current in ('amber', 'red')) or
                    (previous == 'amber' and current == 'red')
                )
            )
            if deteriorated:
                briefing_id = store_briefing({
                    'customer_name':    c['name'],
                    'account_owner':    c.get('account_owner', ''),
                    'health_status':    current,
                    'open_issues':      c.get('open_issues', 0),
                    'risk_level':       'high' if current == 'red' else 'medium',
                    'risk_summary':     f"Health deteriorated {previous} → {current} with {c.get('open_issues', 0)} open issues.",
                    'recommended_action': f"Schedule urgent review with {c.get('account_owner', 'account owner')}.",
                    'urgency':          'high' if current == 'red' else 'medium',
                    'source':           'churn_signal',
                })
                if briefing_id:
                    flagged += 1

            store_health_snapshot(c['name'], current)

        log_event('autonomous', {'action': 'churn_signal', 'flagged': flagged})
    except Exception as exc:
        log_event('autonomous_error', {'action': 'churn_signal', 'error': str(exc)})
    return flagged


def start_autonomous_scheduler() -> None:
    """Start background threads for all autonomous agentic behaviors."""
    def _sweep_worker():
        time.sleep(30)   # brief startup delay
        while True:
            # Distributed lock (870s TTL < 900s interval) prevents duplicate
            # runs across pods. Falls back to running if Redis is unreachable.
            if _try_acquire_lock('lock:health_sweep', 870):
                run_health_sweep()
            time.sleep(900)  # every 15 minutes

    def _churn_worker():
        time.sleep(90)
        while True:
            # Distributed lock (82800s ≈ 23h TTL < 24h interval).
            if _try_acquire_lock('lock:churn_signal', 82800):
                run_churn_signal()
            time.sleep(86400)  # daily

    threading.Thread(target=_sweep_worker, daemon=True, name='health-sweep').start()
    threading.Thread(target=_churn_worker, daemon=True, name='churn-signal').start()
