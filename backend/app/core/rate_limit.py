"""Rate limiting for auth endpoints (Phase 2.2, docs/IMPROVEMENT-PLAN.md).

In-memory token-bucket via slowapi, keyed on client IP. This bounds **password
spray** — one attacker walking many emails from a single IP.

It does **not** bound **credential stuffing** — many IPs against one known
email. That needs an email-scoped key, which is not wired: an earlier
``_email_key`` helper existed but was never referenced by any limiter, and the
request state it read from was never populated. It has been removed rather than
left as a claim the code doesn't honour. Adding a real email-scoped limiter
changes when callers receive 429, so it belongs in its own change with tests
(see docs/AUDIT-2026-08.md, M2).

The in-memory backend is fine for a single-instance free-tier deploy. A
production fleet behind a load balancer would set
``RATE_LIMIT_STORAGE_URL=redis://…`` and reuse the same limiter so multi-replica
deploys count requests across all instances.
"""

from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _client_ip(request: Request) -> str:
    """Client IP as slowapi sees it — ``request.client.host``.

    Note this reads the *socket* peer, not ``X-Forwarded-For``. Behind a proxy
    the real client IP arrives because uvicorn runs with ``--proxy-headers``
    (see backend/Dockerfile), which rewrites ``request.client`` before the app
    is reached. Drop that flag and every request buckets under the proxy's IP.
    """
    return get_remote_address(request)


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
