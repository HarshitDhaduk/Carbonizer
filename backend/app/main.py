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


app = FastAPI(
    title=settings.project_name,
    version="0.1.0",
    description=(
        "Personal carbon tracking API. Automated ingestion (Open Banking, "
        "telematics, smart meter), CO2e accounting, behavioral nudges, and "
        "privacy-first data rights. See docs/API-DESIGN.md."
    ),
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
