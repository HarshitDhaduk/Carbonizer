"""CSRF protection via double-submit cookie (Phase 2.1, docs/IMPROVEMENT-PLAN.md).

Cookies sent automatically by the browser are the classic CSRF attack vector.
Even with SameSite=Lax (which blocks cross-site form posts), a same-site
attacker — say a comment with an embedded ``<img src=…>`` pointing at our API
on a sibling subdomain — can still issue a state-changing request and have the
browser attach the access cookie.

The double-submit pattern adds a custom header that the attacker can't set:

  1. On login, the backend issues a non-HttpOnly ``cb_csrf`` cookie alongside
     the HttpOnly ``cb_access`` cookie.
  2. The frontend reads ``cb_csrf`` via ``document.cookie`` and echoes it as
     the ``X-CSRF-Token`` header on every POST / PUT / PATCH / DELETE.
  3. This middleware compares the two with a constant-time check and rejects
     the request with 403 on any mismatch.

A cross-origin attacker can neither read the victim's ``cb_csrf`` cookie
(browser's same-origin policy) nor set arbitrary headers on a fetch from the
attacker's page (the browser refuses custom headers without a CORS preflight
that our backend won't authorize).

Bearer-authenticated requests skip the check entirely — those tokens are not
sent automatically, so they're inherently not vulnerable to CSRF. This keeps
the OpenAPI ``/docs`` Swagger UI and any machine clients working unchanged.
"""

from __future__ import annotations

import hmac
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Endpoints that ISSUE the CSRF cookie — they can't require it as a precondition.
# Path matching is prefix-based so a future ``/auth/login/foo`` would also be
# exempt; we keep this list tight.
_EXEMPT_PATHS: tuple[str, ...] = (
    f"{settings.api_v1_prefix}/auth/login",
    f"{settings.api_v1_prefix}/auth/register",
    f"{settings.api_v1_prefix}/auth/refresh",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Reject state-changing, cookie-authenticated requests without a matching CSRF token."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method in _SAFE_METHODS:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in _EXEMPT_PATHS):
            return await call_next(request)

        # Only enforce CSRF when the request is using cookie auth. Bearer-auth
        # requests (machine clients, /docs, our own tests) don't need it.
        if settings.access_cookie_name not in request.cookies:
            return await call_next(request)

        cookie_token = request.cookies.get(settings.csrf_cookie_name) or ""
        header_token = request.headers.get("x-csrf-token") or ""

        # Reject empties first so compare_digest doesn't get a free "match" on
        # two empty strings.
        if not cookie_token or not header_token:
            return _forbidden("CSRF token missing")
        if not hmac.compare_digest(cookie_token, header_token):
            return _forbidden("CSRF token mismatch")
        return await call_next(request)


def _forbidden(detail: str) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": detail})
