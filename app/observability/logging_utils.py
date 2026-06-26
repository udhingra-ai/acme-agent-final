import json, time, functools
from datetime import datetime, timezone

# Level mapping: kind suffix determines log level emitted in the `level` field.
# Consumers (Datadog, CloudWatch, log grep) can filter on `level`.
_LEVEL_MAP = {
    '_error': 'ERROR',
    '_warn': 'WARN',
    'error': 'ERROR',
    'warn': 'WARN',
}


def log_event(kind: str, payload: dict, level: str = '') -> None:
    if not level:
        for suffix, lvl in _LEVEL_MAP.items():
            if kind.endswith(suffix) or kind == suffix:
                level = lvl
                break
        else:
            level = 'INFO'
    print(json.dumps(
        {'ts': datetime.now(timezone.utc).isoformat(), 'level': level, 'kind': kind, 'payload': payload},
        default=str,
    ))


def timed(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = fn(*args, **kwargs)
        elapsed_ms = round((time.time() - start) * 1000, 2)
        log_event('timing', {'function': fn.__name__, 'elapsed_ms': elapsed_ms})
        return result
    return wrapper
