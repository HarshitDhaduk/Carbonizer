"""Onboarding questionnaire answers — one row per user (docs/DATA-STRATEGY.md §4).

Captures the inputs to the Day-0 footprint estimate. The computed estimate itself is
persisted via `footprint_snapshots` (method=estimated), not here — this table is just the
normalized source answers so a user can revisit/refine them.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import CarType, Diet, EnergySource, HomeType, OnboardingStatus


class OnboardingProfile(Base, TimestampMixin):
    """1:1 with users — `user_id` is the primary key (no surrogate).

    Persists *partial* progress: a row is created as soon as onboarding starts
    (status=in_progress) and autosaved on each step, so closing the app mid-flow
    resumes at `current_step`. `status` flips to completed on estimate submission.
    """

    __tablename__ = "onboarding_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    # progress tracking (server_default keeps the migration safe on existing rows)
    status: Mapped[OnboardingStatus] = mapped_column(
        default=OnboardingStatus.in_progress,
        server_default=OnboardingStatus.in_progress.value,
        nullable=False,
    )
    current_step: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )

    household_size: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    home_type: Mapped[HomeType] = mapped_column(default=HomeType.terraced, nullable=False)
    energy_source: Mapped[EnergySource] = mapped_column(
        default=EnergySource.standard, nullable=False
    )
    diet: Mapped[Diet] = mapped_column(default=Diet.average, nullable=False)
    car_type: Mapped[CarType] = mapped_column(default=CarType.petrol, nullable=False)
    car_km_per_week: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    short_flights_per_year: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    long_flights_per_year: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
