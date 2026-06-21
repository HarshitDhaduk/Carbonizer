"""HTTP cache helpers — Phase 4.1 of docs/IMPROVEMENT-PLAN.md.

Per-route `Cache-Control` directives are set explicitly on the response so
intermediaries (browser, CDN, Cloudflare in production) cache exactly as long
as our consistency model allows:

  * footprint summary — `private, max-age=60`   (per-user; revalidate often)
  * community benchmark — `private, max-age=300` (per-user, slower-moving)
  * onboarding questions — `public, max-age=3600, immutable` (server-defined,
    versioned via QUESTIONNAIRE_VERSION; safe to share)

ETag generation is opt-in via :func:`set_etag` — call it on routes whose
payload has a stable identity (e.g. the questionnaire bumps its ETag when
QUESTIONNAIRE_VERSION changes, so clients get a 304 the rest of the time).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from fastapi import HTTPException, Request, Response, status


def cache_private(response: Response, *, max_age: int) -> None:
    """Mark the response cacheable per-user only for ``max_age`` seconds."""
    response.headers["Cache-Control"] = f"private, max-age={max_age}"


def cache_public_immutable(response: Response, *, max_age: int) -> None:
    """Mark the response cacheable for anyone for ``max_age`` seconds and not
    revalidatable within that window — for content with a version-cut identity."""
    response.headers["Cache-Control"] = (
        f"public, max-age={max_age}, immutable"
    )


def compute_etag(*parts: object) -> str:
    """Build a stable, quoted ETag from a tuple of identity components.

    Order matters — pass the version first, then any user-discriminating
    inputs. The hash is truncated to 16 hex chars (64 bits) — collision-resistant
    for cache identity at our scale and keeps headers small.
    """
    h = hashlib.sha256()
    for p in parts:
        h.update(repr(p).encode("utf-8"))
    return f'"{h.hexdigest()[:16]}"'


def set_etag(
    request: Request, response: Response, *, parts: Iterable[object]
) -> None:
    """Set ``ETag`` on the response and raise HTTP 304 if the client already
    has it.

    Pattern:

        @router.get("/foo")
        async def foo(request: Request, response: Response):
            set_etag(request, response, parts=(version, user_id))
            cache_private(response, max_age=60)
            return payload
    """
    etag = compute_etag(*parts)
    response.headers["ETag"] = etag
    if request.headers.get("if-none-match") == etag:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED)
