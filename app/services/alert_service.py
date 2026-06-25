"""
Alert deduplication — prevents the same alert from firing every 60-second poll.
Uses Redis TTL as a sliding window: if the key exists, the alert was already sent.
"""
from core.redis_client import r

_DEDUP_TTL = 3600  # suppress repeat alerts for 1 hour


def should_send_alert(customer_name: str, alert_type: str) -> bool:
    """Return True if this alert should fire now, and mark it as sent."""
    key = f'alert:dedup:{alert_type}:{customer_name}'
    try:
        if r.exists(key):
            return False
        r.setex(key, _DEDUP_TTL, '1')
        return True
    except Exception:
        return True  # fail open — better to over-alert than to suppress


def clear_alert(customer_name: str, alert_type: str) -> None:
    """Call when a user acknowledges/resolves an alert to allow re-firing."""
    key = f'alert:dedup:{alert_type}:{customer_name}'
    try:
        r.delete(key)
    except Exception:
        pass
