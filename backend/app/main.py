"""Carbonizer FastAPI application entrypoint.

Run:  uvicorn app.main:app --reload
Docs: http://localhost:8000/docs  ·  OpenAPI: /api/v1/openapi.json
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.csrf import CSRFMiddleware
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.core.request_id import RequestIdMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.session import dispose_engine

logger = logging.getLogger("carbonizer")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info(
        "Starting %s (env=%s, use_db=%s)",
        settings.project_name,
        settings.environment,
        settings.use_db,
    )
    yield
    await dispose_engine()
    logger.info("Shutdown complete")


_TAG_METADATA = [
    {"name": "auth", "description": "Sign in / register / refresh / logout. JWT lives in HttpOnly cookies (ADR-0003)."},
    {"name": "onboarding", "description": "Server-defined questionnaire + Day-0 estimator + autosave (ADR-0001)."},
    {"name": "footprint", "description": "Dashboard summary + R3 behavioural-vs-grid attribution."},
    {"name": "recommendations", "description": "Behavioural nudges, ranked by carbon x money savings."},
    {"name": "community", "description": "k-anonymised cohort benchmarks with IPW + Laplace DP (R4)."},
    {"name": "connections", "description": "Bank / telematics / meter link + sync + disconnect (sandbox today)."},
    {"name": "ingest", "description": "Provider sync surfaces — exposed for tooling, called by `connections`."},
    {"name": "privacy", "description": "GDPR / DPDP data-rights handlers: export, erase with 48-h grace."},
    {"name": "health", "description": "Liveness probe (intentionally cheap, no DB ping)."},
]

app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    summary="Personal carbon tracking + data-rights API.",
    description=(
        "**Carbonizer** turns connected bank / telematics / smart-meter data "
        "into a CO2e footprint with measured confidence, plus the behavioural "
        "nudges that shrink it.\n\n"
        "Highlights:\n\n"
        "- **HttpOnly cookies** for auth — XSS can't lift the session (see "
        "[ADR-0003](https://github.com/HarshitDhaduk/Carbonizer/blob/main/docs/adr/0003-jwt-in-cookies.md)). "
        "Bearer is still accepted for tooling and Swagger.\n"
        "- **Server-defined questionnaire** ([ADR-0001](https://github.com/HarshitDhaduk/Carbonizer/blob/main/docs/adr/0001-server-defined-questionnaire.md)) "
        "with ETag + `Cache-Control: public, max-age=3600, immutable`.\n"
        "- **R0/R1/R2/R4** ship as transparent heuristics with an ML seam "
        "([ADR-0002](https://github.com/HarshitDhaduk/Carbonizer/blob/main/docs/adr/0002-heuristics-with-ml-seam.md)).\n"
        "- **Partitioned `raw_*` tables** for retention + scan bounds "
        "([ADR-0004](https://github.com/HarshitDhaduk/Carbonizer/blob/main/docs/adr/0004-partition-raw-tables.md)).\n\n"
        "See [`docs/API-DESIGN.md`](https://github.com/HarshitDhaduk/Carbonizer/blob/main/docs/API-DESIGN.md) "
        "for the full contract, [`docs/SECURITY-REVIEW.md`](https://github.com/HarshitDhaduk/Carbonizer/blob/main/docs/SECURITY-REVIEW.md) "
        "for the OWASP self-review."
    ),
    contact={
        "name": "Carbonizer",
        "url": "https://github.com/HarshitDhaduk/Carbonizer",
    },
    license_info={"name": "MIT"},
    openapi_tags=_TAG_METADATA,
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# In development, allow any localhost/127.0.0.1 port (dev servers pick random
# ports), so browser-side calls aren't blocked by CORS. Production uses the
# explicit allowlist only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=(
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
        if not settings.is_production
        else None
    ),
)

app.add_middleware(SecurityHeadersMiddleware)
# Request-id middleware sits outside everything so every log line — including
# the slowapi 429 handler and the CSRF rejection — carries the same id.
app.add_middleware(RequestIdMiddleware)
# CSRF middleware after CORS so preflight OPTIONS still gets a CORS-correct
# response, before SlowAPI so a rejected CSRF attempt isn't counted against
# the rate budget of a legitimate caller.
app.add_middleware(CSRFMiddleware)
app.add_middleware(SlowAPIMiddleware)
# Phase 4.5 — GZip JSON bodies > ~1KB. Brotli is left to the CDN edge in
# production where it's a lot cheaper than burning CPU per-response here.
app.add_middleware(GZipMiddleware, minimum_size=1000)

# slowapi state + 429 handler. slowapi's handler is typed against its own
# RateLimitExceeded subclass; Starlette wants the broader Exception signature.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.include_router(api_router, prefix=settings.api_v1_prefix)


# Phase 4.3 — Prometheus scrape endpoint. We export the default
# `prometheus_client` registry: process-resident memory, CPU seconds, GC stats,
# file descriptors. Per-request latency histograms are intentionally not
# wired here — the high-level fastapi instrumentator has a known
# incompatibility with FastAPI 0.138's `_IncludedRouter` (it crashes during
# its route-name lookup). A focused follow-up will swap in a compatible
# alternative or contribute the patch upstream.
@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {
        "name": settings.project_name,
        "docs": "/docs",
        "api": settings.api_v1_prefix,
    }
