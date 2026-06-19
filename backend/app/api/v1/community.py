"""Community endpoints — k-anonymized aggregates only."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user
from app.db.session import get_db
from app.schemas.community import Benchmark
from app.services import dashboard

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/benchmark", response_model=Benchmark)
async def get_benchmark(
    db: AsyncSession | None = Depends(get_db),
    subject: str | None = Depends(get_optional_user),
) -> Benchmark:
    return await dashboard.get_benchmark(db, subject)
