import httpx
from core.config import KEYCLOAK_SERVER_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID

TOKEN_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"


def get_password_token(username: str, password: str):
    payload = {
        'grant_type': 'password',
        'client_id': KEYCLOAK_CLIENT_ID,
        'username': username,
        'password': password,
    }
    with httpx.Client(timeout=15.0) as client:
        r = client.post(TOKEN_URL, data=payload)
        r.raise_for_status()
        return r.json()
