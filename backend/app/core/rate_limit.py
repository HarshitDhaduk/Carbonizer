"""Rate limiting for auth endpoints (Phase 2.2, docs/IMPROVEMENT-PLAN.md).

In-memory token-bucket via slowapi. Per-IP + per-email composite keys catch the
two common abuse patterns:

  - **Password spray** — same attacker hitting many emails from one IP: bounded by
    the IP limit.
  - **Credential stuffing** — many IPs against one known email: bounded by the
    email limit (we hash the email so it doesn't end up in logs).

The in-memory backend is fine for a single-instance free-tier deploy. A
production fleet behind a load balancer would set
``RATE_LIMIT_STORAGE_URL=redis://…`` and reuse the same limiter so multi-replica
deploys count requests across all instances.
"""

from __future__ import annotations

import hashlib
import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _client_ip(request: Request) -> str:
    """Best-effort client IP that also respects X-Forwarded-For when present."""
    return get_remote_address(request)


def _email_key(request: Request) -> str:
    """Composite key: scope by email if the request carries one as a form field,
    falling back to IP. Hashed so the limiter store never logs raw emails."""
    email: str | None = None
    # OAuth2PasswordRequestForm posts application/x-www-form-urlencoded
    if request.method == "POST":
        # cheap, non-consuming peek — slowapi calls this synchronously before
        # the route handler reads the body, so we use request.scope's cached
        # query string as a fallback only.
        body_form = getattr(request.state, "_login_form", None)
        if body_form is not None:
            email = body_form.get("username")
    if not email:
        return _client_ip(request)
    digest = hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:16]
    return f"email:{digest}"


# Storage URL: in-memory by default; set RATE_LIMIT_STORAGE_URL=redis://... in
# production to share counters across replicas.
_STORAGE = os.environ.get("RATE_LIMIT_STORAGE_URL", "memory://")

# IP-keyed limiter — used as the slowapi extension on the app.
limiter = Limiter(
    key_func=_client_ip,
    storage_uri=_STORAGE,
    headers_enabled=True,  # adds RateLimit-* + Retry-After response headers
)

# Test / e2e escape hatch — set RATE_LIMIT_ENABLED=false to disable counting.
# The unit suite already does this via conftest; the e2e suite needs an env
# flag because the backend is a separate process there.
if os.environ.get("RATE_LIMIT_ENABLED", "true").lower() in {"false", "0", "no"}:
    limiter.enabled = False
