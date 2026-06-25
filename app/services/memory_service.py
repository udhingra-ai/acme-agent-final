import json
import redis as redis_lib
from core.redis_client import r

_SESSION_TTL = 3600
_PROFILE_TTL = 900
_MAX_HISTORY = 50  # cap per session to prevent unbounded growth


def get_session_context(session_id: str):
    try:
        raw = r.get(f'session:{session_id}')
        return json.loads(raw) if raw else {'history': []}
    except redis_lib.RedisError:
        return {'history': []}


def append_session_event(session_id: str, event: dict):
    try:
        state = get_session_context(session_id)
        history = state.get('history', [])
        history = history[-((_MAX_HISTORY - 1)):]  # keep last N-1 before appending
        history.append(event)
        state['history'] = history
        r.setex(f'session:{session_id}', _SESSION_TTL, json.dumps(state, default=str))
        return state
    except redis_lib.RedisError:
        return {'history': [event]}


def cache_customer_profile(customer_name: str, payload: dict):
    try:
        r.setex(f'customer:{customer_name.lower()}', _PROFILE_TTL, json.dumps(payload, default=str))
    except redis_lib.RedisError:
        pass  # cache miss is recoverable; direct DB will be called next time


def get_cached_customer_profile(customer_name: str):
    try:
        raw = r.get(f'customer:{customer_name.lower()}')
        return json.loads(raw) if raw else None
    except redis_lib.RedisError:
        return None
