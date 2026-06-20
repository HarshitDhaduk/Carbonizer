"""Read services backing the dashboard endpoints.

In seed mode (USE_DB=false) they return in-memory fixtures. With USE_DB=true they
read the demo user's rows from Postgres: footprint_snapshots / recommendations /
cohorts / connections (docs/DB-SCHEMA.md §4–7). If the demo user hasn't been seeded
yet, they fall back to fixtures so the contract always holds.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.community import Cohort, UserCohort
from app.models.connection import Connection
from app.models.emission import FootprintSnapshot
from app.models.enums import NudgeStatus, ProviderKind
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.community import Benchmark
from app.schemas.connection import DataConnection
from app.schemas.footprint import FootprintSummary
from app.schemas.recommendation import Nudge
from app.services import benchmark_stats, seed

# presentation maps for connections (Connection has no label column)
_CONN_LABEL: dict[ProviderKind, str] = {
    ProviderKind.bank: "Bank",
    ProviderKind.telematics: "Travel",
    ProviderKind.meter: "Home energy",
}
_CONN_ORDER: dict[ProviderKind, int] = {
    ProviderKind.bank: 0,
    ProviderKind.telematics: 1,
    ProviderKind.meter: 2,
}


async def _demo_user_id(db: AsyncSession) -> uuid.UUID | None:
    res = await db.execute(select(User.id).where(User.email == settings.demo_email))
    return res.scalar_one_or_none()


async def _resolve_user_id(
    db: AsyncSession, subject: str | None
) -> uuid.UUID | None:
    """The authenticated user's UUID if present, else the demo user."""
    if subject and subject != "usr_demo":
        try:
            return uuid.UUID(subject)
        except ValueError:
            pass
    return await _demo_user_id(db)


def _relative_time(ts: datetime | None) -> str | None:
    """Compact 'time ago' string for the connections list (e.g. '2h ago')."""
    if ts is None:
        return None
    now = datetime.now(UTC)
    delta = now - (ts if ts.tzinfo else ts.replace(tzinfo=UTC))
    secs = int(delta.total_seconds())
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"


async def get_footprint_summary(
    db: AsyncSession | None, range_: str = "12w", subject: str | None = None
) -> FootprintSummary:
    if db is None:
        return seed.seed_summary()
    user_id = await _resolve_user_id(db, subject)
    if user_id is None:
        return seed.seed_summary()
    res = await db.execute(
        select(FootprintSnapshot).where(
            FootprintSnapshot.user_id == user_id,
            FootprintSnapshot.range == range_,
        )
    )
    snapshot = res.scalar_one_or_none()
    if snapshot is None or not snapshot.payload:
        return seed.seed_summary()
    # the snapshot payload is the full summary, stored on (re)compute
    return FootprintSummary.model_validate(snapshot.payload)


async def get_recommendations(
    db: AsyncSession | None, subject: str | None = None
) -> list[Nudge]:
    if db is None:
        return seed.seed_nudges()
    user_id = await _resolve_user_id(db, subject)
    if user_id is None:
        return seed.seed_nudges()
    res = await db.execute(
        select(Recommendation)
        .where(
            Recommendation.user_id == user_id,
            Recommendation.status == NudgeStatus.active,
        )
        .order_by(Recommendation.score.desc())
    )
    rows = res.scalars().all()
    if not rows:
        return seed.seed_nudges()
    return [
        Nudge(
            id=str(row.id),
            kind=row.kind,
            title=row.title,
            detail=row.detail,
            carbon_saved_tco2e=float(row.carbon_saved_tco2e),
            money_saved=row.money_saved_minor / 100,
            currency=row.currency,
            effort=row.effort,
            window_ends_at=row.window_ends_at,
        )
        for row in rows
    ]


async def get_benchmark(
    db: AsyncSession | None, subject: str | None = None
) -> Benchmark:
    if db is None:
        return seed.seed_benchmark()
    user_id = await _resolve_user_id(db, subject)
    if user_id is None:
        return seed.seed_benchmark()

    # user's annualized total from the snapshot
    snap_res = await db.execute(
        select(FootprintSnapshot.total_tco2e).where(
            FootprintSnapshot.user_id == user_id,
            FootprintSnapshot.range == "12w",
        )
    )
    you = snap_res.scalar_one_or_none()

    coh_res = await db.execute(
        select(Cohort)
        .join(UserCohort, UserCohort.cohort_id == Cohort.id)
        .where(UserCohort.user_id == user_id)
    )
    cohort = coh_res.scalar_one_or_none()
    if you is None or cohort is None:
        return seed.seed_benchmark()

    you_f = float(you)
    # R4: lift the eco-skewed connector mean to the population (IPW) and release it
    # with differential privacy. Compare "you vs average" against the corrected mean.
    cohort_seed = int(cohort.id.hex[:8], 16)
    avg = benchmark_stats.adjusted_average(float(cohort.avg_tco2e), cohort_seed)
    vs = round((you_f - avg) / avg * 100) if avg else 0
    # k-anonymity: hide the cohort size below the threshold (DB-SCHEMA §7)
    cohort_size = cohort.size if cohort.size >= 50 else None
    return Benchmark(
        you_tco2e=you_f,
        average_tco2e=avg,
        top_tco2e=float(cohort.top_tco2e),
        vs_average_pct=vs,
        cohort_size=cohort_size,
        privacy_adjusted=True,
    )


async def get_connections(
    db: AsyncSession | None, subject: str | None = None
) -> list[DataConnection]:
    if db is None:
        return seed.seed_connections()
    user_id = await _resolve_user_id(db, subject)
    if user_id is None:
        return seed.seed_connections()
    res = await db.execute(
        select(Connection).where(Connection.user_id == user_id)
    )
    rows = res.scalars().all()
    if not rows:
        return seed.seed_connections()
    rows = sorted(rows, key=lambda c: _CONN_ORDER.get(c.provider, 9))
    return [
        DataConnection(
            id=row.provider.value,  # bank | telematics | meter
            label=_CONN_LABEL.get(row.provider, row.provider.value.title()),
            # DB enum 'needs_attention' → wire literal 'needs-attention'
            status=row.status.value.replace("_", "-"),
            last_sync=_relative_time(row.last_sync_at),
        )
        for row in rows
    ]
