"""Shared FastAPI dependencies: auth extraction and the current user.

Two auth modes are supported:

  * **Cookie auth** (the SPA path) — the access JWT lives in the HttpOnly
    ``cb_access`` cookie, set by ``/auth/login`` and friends. CSRF protection
    is enforced separately by :mod:`app.core.csrf`.
  * **Bearer auth** (Swagger UI, machine clients, our own tests) — the JWT is
    sent in the ``Authorization`` header. Tokens lifted from localStorage are
    no longer a thing for the SPA, so this mode is only for non-browser
    callers.

Cookie is preferred when both are present.
"""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.security import decode_token

# auto_error=False → endpoints can treat auth as optional (the demo dashboard is
# public). We still declare this so FastAPI's OpenAPI schema advertises Bearer
# auth in /docs.
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
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None


def _extract_token(request: Request, bearer: str | None) -> str | None:
    """Cookie first, Bearer second."""
    cookie_token = request.cookies.get(settings.access_cookie_name)
    if cookie_token:
        return cookie_token
    return bearer


async def get_optional_user(
    request: Request, bearer: str | None = Depends(oauth2_scheme)
) -> str | None:
    """Return the user subject if a valid token is present, else None."""
    return _subject_from_token(_extract_token(request, bearer))


async def require_user(
    request: Request, bearer: str | None = Depends(oauth2_scheme)
) -> str:
    """Require a valid access token; raise 401 otherwise."""
    subject = _subject_from_token(_extract_token(request, bearer))
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject
