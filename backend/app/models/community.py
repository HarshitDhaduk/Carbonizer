"""Cohorts, membership, and challenges (DB-SCHEMA §7). Aggregates are k-anonymized."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class Cohort(Base, TimestampMixin):
    """A k-anonymised peer group. Unique on (size band, income band, region);
    populated by an offline job that ensures every cohort has ≥ k members
    before any aggregate is released to the dashboard."""

    __tablename__ = "cohorts"
    __table_args__ = (
        UniqueConstraint(
            "household_size_band", "income_band", "region", name="uq_cohort"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    household_size_band: Mapped[str] = mapped_column(String, nullable=False)
    income_band: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0)
    avg_tco2e: Mapped[float] = mapped_column(Numeric(8, 3), default=0)
    top_tco2e: Mapped[float] = mapped_column(Numeric(8, 3), default=0)


class UserCohort(Base):
    """User ↔ cohort link table (composite PK on user_id)."""

    __tablename__ = "user_cohort"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    cohort_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False
    )


class Challenge(Base, TimestampMixin):
    """A community-wide challenge (cycle-to-work month, etc). target_metric is
    JSONB so per-challenge bookkeeping doesn't need a schema migration."""

    __tablename__ = "challenges"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    target_metric: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class ChallengeParticipant(Base):
    """User ↔ challenge link with a participation timestamp and progress (0..1)."""

    __tablename__ = "challenge_participants"

    challenge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    progress: Mapped[float] = mapped_column(Float, default=0)
