import json
from core.redis_client import r


def get_session_context(session_id: str):
    raw = r.get(f'session:{session_id}')
    return json.loads(raw) if raw else {'history': []}


def append_session_event(session_id: str, event: dict):
    state = get_session_context(session_id)
    state['history'].append(event)
    r.setex(f'session:{session_id}', 3600, json.dumps(state, default=str))
    return state


def cache_customer_profile(customer_name: str, payload: dict):
    r.setex(f'customer:{customer_name.lower()}', 900, json.dumps(payload, default=str))


def get_cached_customer_profile(customer_name: str):
    raw = r.get(f'customer:{customer_name.lower()}')
    return json.loads(raw) if raw else None
