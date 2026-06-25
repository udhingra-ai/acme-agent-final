from typing import List, Optional
from fastapi import Header, HTTPException
from jose import jwt
import httpx
from core.config import KEYCLOAK_JWKS_URL, KEYCLOAK_CLIENT_ID, APP_ENV, KEYCLOAK_SERVER_URL, KEYCLOAK_REALM

# Derived at import time so it never needs passing as an argument
KEYCLOAK_ISSUER = f'{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}'

_jwks_cache = None

def _get_jwks():
    global _jwks_cache
    if _jwks_cache is None and KEYCLOAK_JWKS_URL:
        try:
            with httpx.Client(timeout=10.0) as client:
                _jwks_cache = client.get(KEYCLOAK_JWKS_URL).json()
        except Exception:
            _jwks_cache = {"keys": []}
    return _jwks_cache or {"keys": []}


def _decode_token(token: str):
    jwks = _get_jwks()
    unverified = jwt.get_unverified_header(token)
    kid = unverified.get('kid')
    keys = jwks.get('keys', [])
    key = next((k for k in keys if k.get('kid') == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail='Unable to find signing key')
    return jwt.decode(token, key, algorithms=['RS256'], issuer=KEYCLOAK_ISSUER, options={"verify_aud": False})


def _roles_from_claims(claims: dict) -> List[str]:
    realm_roles = claims.get('realm_access', {}).get('roles', [])
    client_roles = claims.get('resource_access', {}).get(KEYCLOAK_CLIENT_ID, {}).get('roles', [])
    return sorted(list(set(realm_roles + client_roles)))


def get_user_context(authorization: Optional[str] = Header(default=None), x_role: Optional[str] = Header(default=None), x_user: Optional[str] = Header(default='demo.user')):
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
