import time
from typing import List, Optional
from fastapi import Header, HTTPException
from jose import jwt
import httpx
from core.config import KEYCLOAK_JWKS_URL, KEYCLOAK_CLIENT_ID, APP_ENV, KEYCLOAK_SERVER_URL, KEYCLOAK_REALM

KEYCLOAK_ISSUER = f'{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}'

# JWKS cache with TTL — refreshed every 5 minutes so key rotation
# doesn't require an app restart. Falls back to the stale cache on fetch error
# rather than blocking all auth requests.
_jwks_cache: dict = {"keys": []}
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 300  # seconds


def _get_jwks() -> dict:
    global _jwks_cache, _jwks_fetched_at
    now = time.monotonic()
    if now - _jwks_fetched_at < _JWKS_TTL:
        return _jwks_cache
    if not KEYCLOAK_JWKS_URL:
        return {"keys": []}
    try:
        with httpx.Client(timeout=10.0) as client:
            fresh = client.get(KEYCLOAK_JWKS_URL).json()
        _jwks_cache = fresh
        _jwks_fetched_at = now
    except Exception:
        # Keep stale cache on transient error; next request will retry
        _jwks_fetched_at = now - _JWKS_TTL + 30  # retry in 30 s, not immediately
    return _jwks_cache


def _decode_token(token: str) -> dict:
    jwks = _get_jwks()
    unverified = jwt.get_unverified_header(token)
    kid = unverified.get('kid')
    key = next((k for k in jwks.get('keys', []) if k.get('kid') == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail='Unable to find signing key')

    claims = jwt.decode(
        token, key,
        algorithms=['RS256'],
        issuer=KEYCLOAK_ISSUER,
        options={"verify_aud": False},
    )

    # Validate authorized party — Keycloak doesn't emit an aud claim by default,
    # but azp (authorized party) identifies which client requested the token.
    # Reject tokens issued for a different client on the same realm.
    azp = claims.get('azp', '')
    if azp and azp != KEYCLOAK_CLIENT_ID:
        raise HTTPException(status_code=401, detail='Token not issued for this client')

    return claims


def _roles_from_claims(claims: dict) -> List[str]:
    realm_roles = claims.get('realm_access', {}).get('roles', [])
    client_roles = claims.get('resource_access', {}).get(KEYCLOAK_CLIENT_ID, {}).get('roles', [])
    return sorted(list(set(realm_roles + client_roles)))


def get_user_context(
    authorization: Optional[str] = Header(default=None),
    x_role: Optional[str] = Header(default=None),
    x_user: Optional[str] = Header(default='demo.user'),
) -> dict:
    if authorization and authorization.lower().startswith('bearer '):
        token = authorization.split(' ', 1)[1].strip()
        try:
            claims = _decode_token(token)
            username = claims.get('preferred_username') or claims.get('sub') or 'unknown'
            roles = _roles_from_claims(claims)
            if not roles:
                raise HTTPException(status_code=403, detail='No roles in token')
            return {'username': username, 'roles': roles, 'auth_mode': 'bearer_token'}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=401, detail=f'Invalid bearer token: {e}')

    if APP_ENV == 'local':
        role = x_role or 'sales_user'
        if role not in ['sales_user', 'support_user', 'admin']:
            raise HTTPException(status_code=403, detail='Invalid role')
        return {'username': x_user, 'roles': [role], 'auth_mode': 'local_header_override'}

    raise HTTPException(status_code=401, detail='Bearer token required')


def require_role(user_ctx: dict, allowed: List[str]):
    if not any(r in allowed for r in user_ctx['roles']):
        raise HTTPException(status_code=403, detail='Insufficient role')
