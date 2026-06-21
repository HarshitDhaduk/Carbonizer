"""Seed the database with the demo user's real rows.

Idempotent: re-running wipes the demo user (cascades) + demo cohort and reinserts.
Creates tables via metadata.create_all (Alembic is wired in alembic/ for the
production migration path; this script is the fast local route).

Run (after provisioning the DB — see scripts/provision_db.sql):

    cd backend
    python -m app.db.seed_db
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_engine
from app.models import (
    Cohort,
    Connection,
    FootprintSnapshot,
    OnboardingProfile,
    PrivacySettings,
    RawEnergyRead,
    RawTransaction,
    RawTrip,
    Recommendation,
    User,
    UserCohort,
)
from app.models.enums import (
    CarType,
    ConnStatus,
    Diet,
    EnergySource,
    HomeType,
    NudgeEffort,
    NudgeKind,
    NudgeStatus,
    OnboardingStatus,
    ProviderKind,
)
from app.schemas.community import Benchmark
from app.schemas.footprint import FootprintSummary
from app.schemas.recommendation import Nudge
from app.services import seed


def _money_to_minor(major: float) -> int:
    return round(major * 100)


async def _create_tables() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_DEMO_COHORT_KEY = {
    "household_size_band": "3-4",
    "income_band": "med",
    "region": "GB",
}


async def _wipe_previous(db: AsyncSession) -> None:
    """Idempotent reset — drop any previous demo user and their cohort."""
    existing = await db.execute(
        select(User.id).where(User.email == settings.demo_email)
    )
    old_id = existing.scalar_one_or_none()
    if old_id is not None:
        # raw_* tables FK users without ON DELETE CASCADE — purge first;
        # the user cascade handles privacy/connections/recs/snapshots/onboarding.
        for raw in (RawTransaction, RawEnergyRead, RawTrip):
            await db.execute(delete(raw).where(raw.user_id == old_id))
        await db.execute(delete(User).where(User.id == old_id))
    await db.execute(delete(Cohort).where(*[
        getattr(Cohort, k) == v for k, v in _DEMO_COHORT_KEY.items()
    ]))
    await db.flush()


async def _seed_user(db: AsyncSession, target_tco2e: float) -> User:
    """Insert the demo user + their PrivacySettings, return the persisted row."""
    user = User(
        email=settings.demo_email,
        password_hash=hash_password(settings.demo_password),
        region="GB",
        household_size=3,
        income_band="med",
        target_tco2e=target_tco2e,
    )
    user.privacy = PrivacySettings()
    db.add(user)
    await db.flush()
    return user


def _seed_onboarding(db: AsyncSession, user_id: uuid.UUID, now: datetime) -> None:
    """Plant a completed onboarding profile so the demo is a returning user."""
    db.add(
        OnboardingProfile(
            user_id=user_id,
            status=OnboardingStatus.completed,
            current_step=8,
            household_size=3,
            home_type=HomeType.semi,
            energy_source=EnergySource.standard,
            diet=Diet.average,
            car_type=CarType.petrol,
            car_km_per_week=120,
            short_flights_per_year=2,
            long_flights_per_year=1,
            completed_at=now,
        )
    )


def _seed_snapshot(
    db: AsyncSession, user_id: uuid.UUID, summary: FootprintSummary, now: datetime
) -> None:
    """Cache the headline footprint — backs ``GET /footprint/summary`` reads."""
    db.add(
        FootprintSnapshot(
            user_id=user_id,
            range=summary.range,
            total_tco2e=summary.total_tco2e,
            delta_pct=summary.delta_pct,
            status=summary.status,
            health=summary.health,
            target_tco2e=summary.target_tco2e,
            payload=summary.model_dump(mode="json"),
            generated_at=now,
        )
    )


def _seed_recommendations(
    db: AsyncSession, user_id: uuid.UUID, nudges: list[Nudge]
) -> None:
    """Insert nudges ranked by score (preserves fixture order)."""
    for i, n in enumerate(nudges):
        db.add(
            Recommendation(
                user_id=user_id,
                kind=NudgeKind(n.kind),
                title=n.title,
                detail=n.detail,
                carbon_saved_tco2e=n.carbon_saved_tco2e,
                money_saved_minor=_money_to_minor(n.money_saved),
                currency=n.currency,
                effort=NudgeEffort(n.effort),
                window_ends_at=n.window_ends_at,
                score=100 - i * 10,
                status=NudgeStatus.active,
            )
        )


async def _seed_cohort(
    db: AsyncSession, user_id: uuid.UUID, benchmark: Benchmark
) -> None:
    """Create the demo cohort + the user's membership row."""
    cohort = Cohort(
        **_DEMO_COHORT_KEY,
        size=1840,
        avg_tco2e=benchmark.average_tco2e,
        top_tco2e=benchmark.top_tco2e,
    )
    db.add(cohort)
    await db.flush()
    db.add(UserCohort(user_id=user_id, cohort_id=cohort.id))


def _seed_connections(db: AsyncSession, user_id: uuid.UUID, now: datetime) -> None:
    """Wire up the three sample provider connections (bank/telematics/meter)."""
    db.add_all([
        Connection(
            user_id=user_id, provider=ProviderKind.bank,
            status=ConnStatus.connected, external_account_ref="demo-bank-001",
            last_sync_at=now - timedelta(hours=2),
        ),
        Connection(
            user_id=user_id, provider=ProviderKind.telematics,
            status=ConnStatus.connected, external_account_ref="demo-tel-001",
            last_sync_at=now - timedelta(minutes=12),
        ),
        Connection(
            user_id=user_id, provider=ProviderKind.meter,
            status=ConnStatus.needs_attention, external_account_ref="demo-meter-001",
            last_sync_at=None,
        ),
    ])


async def _seed() -> None:
    """Compose the demo dataset — each step is one focused helper above."""
    engine = get_engine()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    summary = seed.seed_summary()
    nudges = seed.seed_nudges()
    benchmark = seed.seed_benchmark()
    now = datetime.now(UTC)

    async with sessionmaker() as db:
        await _wipe_previous(db)
        user = await _seed_user(db, summary.target_tco2e)
        _seed_onboarding(db, user.id, now)
        _seed_snapshot(db, user.id, summary, now)
        _seed_recommendations(db, user.id, nudges)
        await _seed_cohort(db, user.id, benchmark)
        _seed_connections(db, user.id, now)
        await db.commit()


async def main() -> None:
    """One-shot DB seeder — creates tables + demo user + footprint + cohort."""
    print(f"Seeding {settings.database_url} (use_db={settings.use_db})")
    await _create_tables()
    await _seed()
    await get_engine().dispose()
    print(f"✓ Seeded demo user {settings.demo_email} with footprint, "
          "recommendations, cohort and connections.")


if __name__ == "__main__":
    asyncio.run(main())
