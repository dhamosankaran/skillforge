"""JWT token creation/verification and Google OAuth token validation."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from jose import JWTError, jwt

from app.core.config import get_settings

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"


def create_access_token(data: Dict[str, Any]) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {**data, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a signed JWT refresh token with longer expiry."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {**data, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token. Returns payload or None if invalid."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


async def verify_google_token(credential: str) -> Optional[Dict[str, Any]]:
    """Validate a Google ID token and return user info.

    Calls Google's tokeninfo endpoint to verify the token signature,
    expiry, and audience. Returns the decoded user info dict or None.
    """
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GOOGLE_TOKEN_INFO_URL,
            params={"id_token": credential},
        )
    if resp.status_code != 200:
        return None

    data = resp.json()

    # Verify audience matches our client ID
    if settings.google_client_id and data.get("aud") != settings.google_client_id:
        return None

    return {
        "google_id": data.get("sub"),
        "email": data.get("email"),
        "name": data.get("name", data.get("email", "").split("@")[0]),
        "avatar_url": data.get("picture"),
    }
