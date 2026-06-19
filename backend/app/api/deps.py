"""Shared FastAPI dependencies: auth extraction and the current user."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.security import decode_token

# auto_error=False → endpoints can treat auth as optional (demo dashboard is public)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login", auto_error=False
)


def _subject_from_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload.get("sub")


async def get_optional_user(token: str | None = Depends(oauth2_scheme)) -> str | None:
    """Return the user subject if a valid token is present, else None."""
    return _subject_from_token(token)


async def require_user(token: str | None = Depends(oauth2_scheme)) -> str:
    """Require a valid access token; raise 401 otherwise."""
    subject = _subject_from_token(token)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject
