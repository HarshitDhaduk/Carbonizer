"""Password hashing and JWT helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plaintext password with Argon2id (~50ms per call, memory-hard)."""
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time check of ``plain`` against an Argon2id ``hashed`` value.
    Returns False on malformed input rather than raising — auth flow expects bool."""
    try:
        return _pwd.verify(plain, hashed)
    except ValueError:
        return False


def _create_token(subject: str, ttl: timedelta, token_type: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str) -> str:
    """Issue a short-lived (15 min default) access JWT for the given user UUID."""
    return _create_token(
        subject, timedelta(minutes=settings.access_token_ttl_minutes), "access"
    )


def create_refresh_token(subject: str) -> str:
    """Issue a long-lived (30 day default) refresh JWT for the given user UUID."""
    return _create_token(
        subject, timedelta(days=settings.refresh_token_ttl_days), "refresh"
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises jwt.PyJWTError on failure."""
    payload: dict[str, Any] = jwt.decode(
        token, settings.secret_key, algorithms=[settings.algorithm]
    )
    return payload
