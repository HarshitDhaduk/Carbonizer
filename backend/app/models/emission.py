"""Emission-factor catalog, the CO2e ledger, rollups and snapshots (DB-SCHEMA §5)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import BiomeStatus, CalcMethod, Category, SourceType


class EmissionFactor(Base):
    """Slowly-changing catalog; a ledger entry pins the exact factor used."""

    __tablename__ = "emission_factors"
    __table_args__ = (
        Index("ix_ef_lookup", "category", "activity_key", "region", "valid_from"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source: Mapped[str] = mapped_column(String, nullable=False)  # defra/climatiq/eea…
    category: Mapped[Category] = mapped_column(nullable=False)
    activity_key: Mapped[str] = mapped_column(String, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)  # km | kwh | gbp
    factor: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)
    gwp_method: Mapped[str] = mapped_column(String, default="ipcc_ar6_gwp100")
    region: Mapped[str | None] = mapped_column(String)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


class LedgerEntry(Base):
    """Normalized CO2e stream — partitioned by month on occurred_at."""

    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index("ix_ledger_user_time", "user_id", "occurred_at"),
        Index("ix_ledger_user_cat", "user_id", "category", "occurred_at"),
        {"postgresql_partition_by": "RANGE (occurred_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[Category] = mapped_column(nullable=False)
    source_type: Mapped[SourceType] = mapped_column(nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(nullable=False)  # FK-by-convention
    method: Mapped[CalcMethod] = mapped_column(nullable=False)
    co2e_kg: Mapped[float] = mapped_column(Float, nullable=False)
    factor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("emission_factors.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class CategoryRollup(Base, TimestampMixin):
    """Pre-aggregated buckets powering timeseries + sparklines."""

    __tablename__ = "category_rollups"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[Category] = mapped_column(primary_key=True)
    granularity: Mapped[str] = mapped_column(String, primary_key=True)  # week | month
    bucket_start: Mapped[date] = mapped_column(Date, primary_key=True)
    co2e_kg: Mapped[float] = mapped_column(Float, nullable=False)
    method_mix: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class FootprintSnapshot(Base):
    """Cache for GET /footprint/summary."""

    __tablename__ = "footprint_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "range", name="uq_snapshot_range"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    range: Mapped[str] = mapped_column(String, nullable=False)
    total_tco2e: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    delta_pct: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    status: Mapped[BiomeStatus] = mapped_column(default=BiomeStatus.plateau)
    health: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)
    target_tco2e: Mapped[float | None] = mapped_column(Numeric(8, 3))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
