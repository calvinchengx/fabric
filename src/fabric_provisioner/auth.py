import httpx


def acquire_client_credentials_token(
    *,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    scope: str,
    timeout: float = 60.0,
) -> str:
    """OAuth 2.0 client credentials against the v2.0 token endpoint."""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": scope,
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, data=data)
        response.raise_for_status()
        payload = response.json()
    token = payload.get("access_token")
    if not token:
        msg = "Token response missing access_token"
        raise RuntimeError(msg)
    return str(token)
