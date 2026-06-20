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
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

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
from app.services import seed


def _money_to_minor(major: float) -> int:
    return round(major * 100)


async def _create_tables() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed() -> None:
    engine = get_engine()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    summary = seed.seed_summary()
    nudges = seed.seed_nudges()
    benchmark = seed.seed_benchmark()
    now = datetime.now(UTC)

    async with sessionmaker() as db:
        # --- clean previous demo data (idempotent) ---
        existing = await db.execute(
            select(User.id).where(User.email == settings.demo_email)
        )
        old_id = existing.scalar_one_or_none()
        if old_id is not None:
            # raw_* ingested tables FK users without ON DELETE CASCADE — purge
            # them first, then the user cascade clears the rest (privacy,
            # connections, recommendations, snapshots, onboarding, links).
            for raw in (RawTransaction, RawEnergyRead, RawTrip):
                await db.execute(delete(raw).where(raw.user_id == old_id))
            await db.execute(delete(User).where(User.id == old_id))
        await db.execute(
            delete(Cohort).where(
                Cohort.household_size_band == "3-4",
                Cohort.income_band == "med",
                Cohort.region == "GB",
            )
        )
        await db.flush()

        # --- user + privacy ---
        user = User(
            email=settings.demo_email,
            password_hash=hash_password(settings.demo_password),
            region="GB",
            household_size=3,
            income_band="med",
            target_tco2e=summary.target_tco2e,
        )
        user.privacy = PrivacySettings()
        db.add(user)
        await db.flush()  # assign user.id

        # --- completed onboarding profile (so demo is a "returning user") ---
        db.add(
            OnboardingProfile(
                user_id=user.id,
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

        # --- footprint snapshot (authoritative cache for GET /footprint/summary) ---
        db.add(
            FootprintSnapshot(
                user_id=user.id,
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

        # --- recommendations (ranked by score desc → preserves fixture order) ---
        for i, n in enumerate(nudges):
            db.add(
                Recommendation(
                    user_id=user.id,
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

        # --- cohort + membership ---
        cohort = Cohort(
            household_size_band="3-4",
            income_band="med",
            region="GB",
            size=1840,
            avg_tco2e=benchmark.average_tco2e,
            top_tco2e=benchmark.top_tco2e,
        )
        db.add(cohort)
        await db.flush()
        db.add(UserCohort(user_id=user.id, cohort_id=cohort.id))

        # --- data-source connections ---
        db.add_all(
            [
                Connection(
                    user_id=user.id,
                    provider=ProviderKind.bank,
                    status=ConnStatus.connected,
                    external_account_ref="demo-bank-001",
                    last_sync_at=now - timedelta(hours=2),
                ),
                Connection(
                    user_id=user.id,
                    provider=ProviderKind.telematics,
                    status=ConnStatus.connected,
                    external_account_ref="demo-tel-001",
                    last_sync_at=now - timedelta(minutes=12),
                ),
                Connection(
                    user_id=user.id,
                    provider=ProviderKind.meter,
                    status=ConnStatus.needs_attention,
                    external_account_ref="demo-meter-001",
                    last_sync_at=None,
                ),
            ]
        )

        await db.commit()


async def main() -> None:
    print(f"Seeding {settings.database_url} (use_db={settings.use_db})")
    await _create_tables()
    await _seed()
    await get_engine().dispose()
    print(f"✓ Seeded demo user {settings.demo_email} with footprint, "
          "recommendations, cohort and connections.")


if __name__ == "__main__":
    asyncio.run(main())
