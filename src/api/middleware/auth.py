
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

from src.utils.config import get_settings


class CurrentUser(BaseModel):
    """Identity extracted from a valid access token."""

    user_id: str
    claims: dict[str, Any]


bearer_scheme = HTTPBearer(auto_error=False)


def _credentials_exception() -> HTTPException:
    """Return a consistent 401 response without exposing token details."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz veya eksik erişim tokenı.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_access_token(
    user_id: str,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed, short-lived JWT for an already authenticated user."""
    if not user_id or not user_id.strip():
        raise ValueError("user_id boş olamaz.")

    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": user_id, "iat": now, "exp": expires_at}
    if extra_claims:
        forbidden_claims = {"sub", "iat", "exp"}
        if forbidden_claims & extra_claims.keys():
            raise ValueError("extra_claims, sub, iat veya exp içeremez.")
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_access_token(token: str) -> CurrentUser:
    """Verify JWT signature and expiry, then return its authenticated identity."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "iat", "exp"]},
        )
    except InvalidTokenError as exc:
        raise _credentials_exception() from exc

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise _credentials_exception()

    return CurrentUser(user_id=user_id, claims=payload)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """FastAPI dependency that protects an endpoint with a Bearer JWT."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _credentials_exception()
    return verify_access_token(credentials.credentials)