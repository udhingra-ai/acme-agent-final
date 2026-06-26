import hashlib
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.config import REDIS_URL


def _rate_key(request: Request) -> str:
    """
    Prefer authenticated identity over IP so limits are per-user not per-gateway NAT.

    Key strategy:
      1. Bearer token present → SHA-256 hash of the token (unforgeable in production)
      2. X-User header only → used as-is (spoofable — acceptable in APP_ENV=local only,
         where the bearer path is disabled and X-User is a dev convenience header)
      3. Fallback → remote IP address

    In production (APP_ENV != local), only the bearer-token path is active (security.py
    rejects requests without a valid JWT), so X-User is never trusted for rate-limiting.
    """
    # Check bearer first — highest trust, hash avoids storing raw token in Redis
    auth = request.headers.get('authorization', '')
    if auth.lower().startswith('bearer '):
        token_hash = hashlib.sha256(auth[7:].encode()).hexdigest()[:16]
        return f'token:{token_hash}'
    # Local dev only: X-User header as identity
    user = request.headers.get('x-user', '').strip()
    if user:
        return f'user:{user}'
    return get_remote_address(request)


# Global limiter — Redis-backed so limits are enforced across all pods/replicas.
# Falls back to in-memory if Redis is unavailable (REDIS_URL empty).
limiter = Limiter(key_func=_rate_key, storage_uri=REDIS_URL if REDIS_URL else None)
