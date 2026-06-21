"""Community endpoints — k-anonymized aggregates only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user
from app.core.cache import cache_private
from app.db.session import get_db
from app.schemas.community import Benchmark
from app.services import dashboard

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/benchmark", response_model=Benchmark)
async def get_benchmark(
    response: Response,
    db: AsyncSession | None = Depends(get_db),
    subject: str | None = Depends(get_optional_user),
) -> Benchmark:
    # Cohort aggregates move on the order of hours; 5 minutes is comfortably
    # below the cohort recomputation cadence (docs/API-DESIGN.md §9).
    cache_private(response, max_age=300)
    return await dashboard.get_benchmark(db, subject)
