import json
from sqlalchemy import text
from core.db import SessionLocal


def store_briefing(briefing: dict) -> int | None:
    """
    Insert a briefing row, but skip if an unacknowledged one already exists
    for the same customer + source within the last 30 minutes (dedup).
    Returns the new id, or None if deduped.
    """
    with SessionLocal() as db:
        existing = db.execute(text('''
            SELECT id FROM briefings
            WHERE customer_name = :cn AND source = :src AND acknowledged = FALSE
            AND created_at > NOW() - INTERVAL '30 minutes'
        '''), {'cn': briefing.get('customer_name', ''), 'src': briefing.get('source', '')}).first()
        if existing:
            return None

        row = db.execute(text('''
            INSERT INTO briefings
              (customer_name, account_owner, health_status, open_issues,
               risk_level, risk_summary, recommended_action, urgency,
               source, trigger_issue_id)
            VALUES
              (:customer_name, :account_owner, :health_status, :open_issues,
               :risk_level, :risk_summary, :recommended_action, :urgency,
               :source, :trigger_issue_id)
            RETURNING id
        '''), {
            'customer_name':    briefing.get('customer_name', ''),
            'account_owner':    briefing.get('account_owner', ''),
            'health_status':    briefing.get('health_status', ''),
            'open_issues':      briefing.get('open_issues', 0),
            'risk_level':       briefing.get('risk_level', ''),
            'risk_summary':     briefing.get('risk_summary', ''),
            'recommended_action': briefing.get('recommended_action', ''),
            'urgency':          briefing.get('urgency', ''),
            'source':           briefing.get('source', ''),
            'trigger_issue_id': briefing.get('trigger_issue_id'),
        }).mappings().first()
        db.commit()
        return row['id'] if row else None


def get_recent_briefings(limit: int = 20, account_owner: str = None) -> list:
    """Return recent unacknowledged briefings, optionally filtered by owner."""
    params: dict = {'limit': limit}
    owner_clause = ''
    if account_owner:
        owner_clause = 'AND account_owner = :owner'
        params['owner'] = account_owner
    sql = f'''
        SELECT id, customer_name, account_owner, health_status, open_issues,
               risk_level, risk_summary, recommended_action, urgency,
               source, trigger_issue_id, acknowledged, created_at
        FROM briefings
        WHERE acknowledged = FALSE {owner_clause}
        ORDER BY created_at DESC
        LIMIT :limit
    '''
    with SessionLocal() as db:
        rows = db.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]


def acknowledge_briefing(briefing_id: int, account_owner: str = None) -> bool:
    """
    Acknowledge a briefing. If account_owner is provided, only match rows
    owned by that user (prevents users from dismissing others' briefings).
    """
    params: dict = {'id': briefing_id}
    owner_clause = ''
    if account_owner:
        owner_clause = 'AND account_owner = :owner'
        params['owner'] = account_owner
    with SessionLocal() as db:
        result = db.execute(
            text(f'UPDATE briefings SET acknowledged = TRUE WHERE id = :id {owner_clause}'),
            params
        )
        db.commit()
        return result.rowcount > 0


def get_last_health_snapshot(customer_name: str) -> str | None:
    with SessionLocal() as db:
        row = db.execute(
            text('SELECT health_status FROM health_snapshots WHERE customer_name = :cn'),
            {'cn': customer_name}
        ).first()
        return row[0] if row else None


def store_health_snapshot(customer_name: str, health_status: str) -> None:
    with SessionLocal() as db:
        db.execute(text('''
            INSERT INTO health_snapshots (customer_name, health_status, captured_at)
            VALUES (:cn, :hs, NOW())
            ON CONFLICT (customer_name)
            DO UPDATE SET health_status = :hs, captured_at = NOW()
        '''), {'cn': customer_name, 'hs': health_status})
        db.commit()
