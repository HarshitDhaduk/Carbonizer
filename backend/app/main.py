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
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
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
app.add_middleware(SlowAPIMiddleware)

# slowapi state + 429 handler. slowapi's handler is typed against its own
# RateLimitExceeded subclass; Starlette wants the broader Exception signature.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {
        "name": settings.project_name,
        "docs": "/docs",
        "api": settings.api_v1_prefix,
    }
