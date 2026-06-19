"""Recommendation (nudge) endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user
from app.db.session import get_db
from app.schemas.recommendation import Nudge, NudgeActionResult
from app.services import dashboard

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=list[Nudge])
async def list_recommendations(
    db: AsyncSession | None = Depends(get_db),
    subject: str | None = Depends(get_optional_user),
) -> list[Nudge]:
    return await dashboard.get_recommendations(db, subject)


@router.post("/{rec_id}/act", response_model=NudgeActionResult)
async def act_on_recommendation(
    rec_id: str,
    db: AsyncSession | None = Depends(get_db),
    subject: str | None = Depends(get_optional_user),
) -> NudgeActionResult:
    nudges = await dashboard.get_recommendations(db, subject)
    match = next((n for n in nudges if n.id == rec_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return NudgeActionResult(
        id=rec_id, status="acted", realized_saving_tco2e=match.carbon_saved_tco2e
    )


@router.post("/{rec_id}/dismiss", response_model=NudgeActionResult)
async def dismiss_recommendation(
    rec_id: str,
    _user: str | None = Depends(get_optional_user),
) -> NudgeActionResult:
    return NudgeActionResult(id=rec_id, status="dismissed")
