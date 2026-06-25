import json, time, functools
from datetime import datetime

def log_event(kind: str, payload: dict):
    print(json.dumps({'ts': datetime.utcnow().isoformat(), 'kind': kind, 'payload': payload}, default=str))

def timed(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = fn(*args, **kwargs)
        elapsed_ms = round((time.time() - start) * 1000, 2)
        log_event('timing', {'function': fn.__name__, 'elapsed_ms': elapsed_ms})
        return result
    return wrapper
