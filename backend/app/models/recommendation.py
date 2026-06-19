"""Recommendations (nudges) and the actions taken on them (DB-SCHEMA §6)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CHAR,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import NudgeEffort, NudgeKind, NudgeStatus


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_rec_active", "user_id", "score"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[NudgeKind] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str] = mapped_column(String, nullable=False)
    carbon_saved_tco2e: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    money_saved_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    currency: Mapped[str] = mapped_column(CHAR(3), default="GBP")
    effort: Mapped[NudgeEffort] = mapped_column(nullable=False)
    window_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[NudgeStatus] = mapped_column(default=NudgeStatus.active)


class RecommendationAction(Base, TimestampMixin):
    __tablename__ = "recommendation_actions"

    id: Mapped[uuid.UUID] = uuid_pk()
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String, nullable=False)  # acted | dismissed
    realized_saving_tco2e: Mapped[float | None] = mapped_column(Numeric(8, 4))
    acted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
