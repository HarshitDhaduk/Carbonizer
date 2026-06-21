"""Auth cookie issuance (Phase 2.1, docs/IMPROVEMENT-PLAN.md).

Three cookies make up a session:

  * ``cb_access``  — HttpOnly access JWT, short TTL (15 min). Never readable
    from JS, so an XSS payload can't lift it.
  * ``cb_refresh`` — HttpOnly refresh JWT, longer TTL (30 d). Sent only to
    ``/auth/refresh`` (via ``path=`` scoping).
  * ``cb_csrf``    — non-HttpOnly random token used in a double-submit check by
    :mod:`app.core.csrf`. Readable from JS so the client can echo the value
    in the ``X-CSRF-Token`` header.

Cookie names, SameSite and Secure flags come from :mod:`app.core.config`.
SameSite=Lax + Secure-in-prod gives us defence-in-depth on top of the CSRF
header check.
"""

from __future__ import annotations

import secrets

from fastapi import Response

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token

_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 60 * _SECONDS_PER_MINUTE
_SECONDS_PER_DAY = 24 * _SECONDS_PER_HOUR


def _set(
    response: Response,
    *,
    name: str,
    value: str,
    max_age: int,
    http_only: bool,
    path: str = "/",
) -> None:
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=http_only,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=path,
    )


def generate_csrf_token() -> str:
    """Return a fresh CSRF token (URL-safe, ~43 chars / 256 bits of entropy)."""
    return secrets.token_urlsafe(32)


def set_auth_cookies(response: Response, subject: str) -> str:
    """Issue access + refresh + CSRF cookies for ``subject``. Returns the CSRF token.

    Called from ``/auth/login`` and ``/auth/register``. Existing cookies are
    overwritten — re-logging in cycles the refresh JWT and CSRF token, which is
    the desired behavior (a leaked refresh from a previous session is no longer
    accepted once this fires).
    """
    access_ttl = settings.access_token_ttl_minutes * _SECONDS_PER_MINUTE
    refresh_ttl = settings.refresh_token_ttl_days * _SECONDS_PER_DAY
    _set(
        response,
        name=settings.access_cookie_name,
        value=create_access_token(subject),
        max_age=access_ttl,
        http_only=True,
    )
    _set(
        response,
        name=settings.refresh_cookie_name,
        value=create_refresh_token(subject),
        max_age=refresh_ttl,
        http_only=True,
        # Refresh is only ever sent to the refresh endpoint — limits attack
        # surface for the cookie's auto-attach.
        path=f"{settings.api_v1_prefix}/auth",
    )
    csrf = generate_csrf_token()
    _set(
        response,
        name=settings.csrf_cookie_name,
        value=csrf,
        max_age=refresh_ttl,
        http_only=False,  # JS must read this to echo in the header
    )
    return csrf


def clear_auth_cookies(response: Response) -> None:
    """Wipe all three auth cookies. Called by ``/auth/logout``."""
    response.delete_cookie(
        key=settings.access_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=f"{settings.api_v1_prefix}/auth",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
