"""Aggregate all v1 routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    community,
    connections,
    footprint,
    health,
    ingest,
    onboarding,
    privacy,
    recommendations,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(connections.router)
api_router.include_router(ingest.router)
api_router.include_router(onboarding.router)
api_router.include_router(footprint.router)
api_router.include_router(recommendations.router)
api_router.include_router(community.router)
api_router.include_router(privacy.router)
