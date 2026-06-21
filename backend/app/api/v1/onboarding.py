"""Onboarding endpoints — progress autosave + Day-0 footprint estimate
(docs/API-DESIGN.md §10)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.core.cache import cache_public_immutable, set_etag
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.emission import FootprintSnapshot
from app.models.enums import CarType, Diet, EnergySource, HomeType, OnboardingStatus
from app.models.onboarding import OnboardingProfile
from app.schemas.footprint import FootprintSummary
from app.schemas.onboarding import (
    AnswerValue,
    OnboardingAnswers,
    OnboardingProfileOut,
    OnboardingProgress,
    Questionnaire,
)
from app.services import estimator

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def _require_db(db: AsyncSession | None) -> AsyncSession:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Onboarding requires the database (set USE_DB=true).",
        )
    return db


def _user_uuid(subject: str) -> uuid.UUID:
    try:
        return uuid.UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        ) from exc


def _profile_to_answers(p: OnboardingProfile) -> dict[str, AnswerValue]:
    return {
        "householdSize": p.household_size,
        "homeType": p.home_type.value,
        "energySource": p.energy_source.value,
        "diet": p.diet.value,
        "carType": p.car_type.value,
        "carKmPerWeek": p.car_km_per_week,
        "shortFlightsPerYear": p.short_flights_per_year,
        "longFlightsPerYear": p.long_flights_per_year,
    }


def _apply_answers(profile: OnboardingProfile, answers: dict[str, AnswerValue]) -> None:
    """Write normalized answers onto the typed profile columns."""
    profile.household_size = int(answers["householdSize"])
    profile.home_type = HomeType(answers["homeType"])
    profile.energy_source = EnergySource(answers["energySource"])
    profile.diet = Diet(answers["diet"])
    profile.car_type = CarType(answers["carType"])
    profile.car_km_per_week = int(answers["carKmPerWeek"])
    profile.short_flights_per_year = int(answers["shortFlightsPerYear"])
    profile.long_flights_per_year = int(answers["longFlightsPerYear"])


async def _get_or_create_profile(
    db: AsyncSession, uid: uuid.UUID
) -> OnboardingProfile:
    res = await db.execute(
        select(OnboardingProfile).where(OnboardingProfile.user_id == uid)
    )
    profile = res.scalar_one_or_none()
    if profile is None:
        profile = OnboardingProfile(user_id=uid)
        db.add(profile)
    return profile


@router.get("/questions", response_model=Questionnaire)
async def get_questions(request: Request, response: Response) -> Questionnaire:
    """Server-defined questionnaire — the client renders from this.

    Cache-Control: public, max-age=3600, immutable + an ETag keyed on
    ``QUESTIONNAIRE_VERSION``. When the questionnaire is rev'd (a new
    question, a new option), the ETag changes and clients pick up the
    new payload on the next request.
    """
    set_etag(request, response, parts=("questionnaire", estimator.QUESTIONNAIRE_VERSION))
    cache_public_immutable(response, max_age=3600)
    return estimator.build_questionnaire()


@router.get("/profile", response_model=OnboardingProfileOut)
async def get_profile(
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> OnboardingProfileOut:
    db = _require_db(db)
    uid = _user_uuid(subject)
    res = await db.execute(
        select(OnboardingProfile).where(OnboardingProfile.user_id == uid)
    )
    profile = res.scalar_one_or_none()
    if profile is None:
        return OnboardingProfileOut(
            status="in_progress", completed=False, current_step=0, answers=None
        )
    return OnboardingProfileOut(
        status=profile.status.value,
        completed=profile.status is OnboardingStatus.completed,
        current_step=profile.current_step,
        answers=_profile_to_answers(profile),
    )


@router.put("/progress", response_model=OnboardingProfileOut)
@limiter.limit("120/minute")
async def save_progress(
    request: Request,
    body: OnboardingProgress,
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> OnboardingProfileOut:
    """Autosave partial onboarding so a mid-flow close resumes at current_step.
    A no-op once onboarding is completed (we don't downgrade a finished profile)."""
    db = _require_db(db)
    uid = _user_uuid(subject)

    profile = await _get_or_create_profile(db, uid)
    if profile.status is not OnboardingStatus.completed:
        _apply_answers(profile, estimator.normalize_answers(body.answers))
        profile.current_step = max(0, body.current_step)
        profile.status = OnboardingStatus.in_progress
    await db.commit()

    return OnboardingProfileOut(
        status=profile.status.value,
        completed=profile.status is OnboardingStatus.completed,
        current_step=profile.current_step,
        answers=_profile_to_answers(profile),
    )


@router.post("/estimate", response_model=FootprintSummary)
async def post_estimate(
    body: OnboardingAnswers,
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> FootprintSummary:
    db = _require_db(db)
    uid = _user_uuid(subject)

    answers = estimator.normalize_answers(body.answers)
    summary = estimator.estimate(answers)
    now = datetime.now(UTC)

    # 1) finalize the onboarding profile
    profile = await _get_or_create_profile(db, uid)
    _apply_answers(profile, answers)
    profile.status = OnboardingStatus.completed
    profile.current_step = len(estimator.QUESTIONS)
    profile.completed_at = now

    # 2) upsert the footprint snapshot the dashboard reads (method=estimated)
    snap_res = await db.execute(
        select(FootprintSnapshot).where(
            FootprintSnapshot.user_id == uid,
            FootprintSnapshot.range == summary.range,
        )
    )
    snapshot = snap_res.scalar_one_or_none()
    if snapshot is None:
        snapshot = FootprintSnapshot(user_id=uid, range=summary.range)
        db.add(snapshot)
    snapshot.total_tco2e = summary.total_tco2e
    snapshot.delta_pct = summary.delta_pct
    snapshot.status = summary.status
    snapshot.health = summary.health
    snapshot.target_tco2e = summary.target_tco2e
    snapshot.payload = summary.model_dump(mode="json")
    snapshot.generated_at = now

    await db.commit()
    return summary
