"""Security response headers (Phase 2.4, docs/IMPROVEMENT-PLAN.md).

Adds the defensive headers an external scanner (securityheaders.com,
mozilla observatory) expects: HSTS, X-Content-Type-Options, X-Frame-Options,
Referrer-Policy, Permissions-Policy, and a conservative Content-Security-Policy.

The CSP is tuned for an API server — JSON-only responses, no inline scripts, no
embedding. The Next.js frontend ships its own CSP via next.config.mjs (different
needs because it serves HTML).

HSTS is gated on `is_production` because over-eager HSTS in dev pins your
localhost-served browser to HTTPS forever.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

# A strict, API-friendly CSP: nothing renders here, so default-src 'none' is fine.
# The OpenAPI/Swagger UI at /docs needs slightly more, but we let FastAPI's docs
# UI handle its own headers (it strips the global CSP at render time).
_API_CSP = (
    "default-src 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "form-action 'none'"
)

_PERMISSIONS_POLICY = (
    "geolocation=(), camera=(), microphone=(), payment=(), usb=(), "
    "interest-cohort=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Set defensive security response headers on every response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Append HSTS / CSP / X-Frame-Options / Referrer-Policy to the response."""
        response = await call_next(request)
        headers = response.headers

        # Always-on hardening
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", _PERMISSIONS_POLICY)
        headers.setdefault(
            "Cross-Origin-Opener-Policy", "same-origin"
        )
        headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")

        # Don't apply CSP to FastAPI's docs UI — it needs inline scripts/styles
        # from the Swagger CDN to render.
        path = request.url.path
        if not path.startswith(("/docs", "/redoc")):
            headers.setdefault("Content-Security-Policy", _API_CSP)

        # HSTS — only in production, only over HTTPS. Browsers ignore it on http
        # anyway, but emitting it elsewhere is noise (and can lock a dev box
        # into "https only forever" if you ever serve over https locally).
        if settings.is_production:
            headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )

        return response
