import hashlib
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.config import REDIS_URL


def _rate_key(request: Request) -> str:
    """
    Prefer authenticated identity over IP so limits are per-user not per-gateway NAT.
    Local dev: X-User header; production: hash of Bearer token (avoids storing raw token).
    Falls back to IP for unauthenticated calls.
    """
    user = request.headers.get('x-user', '').strip()
    if user:
        return f'user:{user}'
    auth = request.headers.get('authorization', '')
    if auth.lower().startswith('bearer '):
        token_hash = hashlib.sha256(auth[7:].encode()).hexdigest()[:16]
        return f'token:{token_hash}'
    return get_remote_address(request)


# Global limiter — Redis-backed so limits are enforced across all pods/replicas.
# Falls back to in-memory if Redis is unavailable (REDIS_URL empty).
limiter = Limiter(key_func=_rate_key, storage_uri=REDIS_URL if REDIS_URL else None)
