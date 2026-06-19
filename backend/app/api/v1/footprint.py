"""Footprint endpoints — the dashboard's primary data source."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user, require_user
from app.db.session import get_db
from app.schemas.footprint import Attribution, FootprintSummary
from app.services import attribution, dashboard

router = APIRouter(prefix="/footprint", tags=["footprint"])


@router.get("/summary", response_model=FootprintSummary)
async def get_summary(
    range: Annotated[str, Query(pattern="^(12w|6m|1y)$")] = "12w",
    db: AsyncSession | None = Depends(get_db),
    subject: str | None = Depends(get_optional_user),
) -> FootprintSummary:
    return await dashboard.get_footprint_summary(db, range, subject)


@router.get("/attribution", response_model=Attribution)
async def get_attribution(
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> Attribution:
    """R3: split the user's recent energy change into behavioral vs grid effects.
    Requires connected smart-meter data; returns available=false otherwise."""
    if db is None:
        return Attribution(available=False)
    try:
        uid = uuid.UUID(subject)
    except ValueError:
        return Attribution(available=False)
    return await attribution.energy_attribution(db, uid)
