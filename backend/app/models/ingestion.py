"""Raw ingested activity — partitioned by month on the event time (DB-SCHEMA §4).

These hold provider data verbatim and are re-computable into ledger_entries.
Partitioning + the unique (user_id, external_id, time) indexes give idempotent
ingest and O(1) retention drops.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CHAR,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import TripMode


class RawTransaction(Base):
    __tablename__ = "raw_transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", "booked_at", name="ux_txn_ext"),
        {"postgresql_partition_by": "RANGE (booked_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, primary_key=True)
    booked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connections.id"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    mcc: Mapped[str | None] = mapped_column(CHAR(4))
    description: Mapped[str | None] = mapped_column(String)
    merchant: Mapped[str | None] = mapped_column(String)
    spend_region: Mapped[str | None] = mapped_column(String)
    commodity_class: Mapped[str | None] = mapped_column(String)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RawTrip(Base):
    __tablename__ = "raw_trips"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", "started_at", name="ux_trip_ext"),
        {"postgresql_partition_by": "RANGE (started_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connections.id"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mode: Mapped[TripMode] = mapped_column(nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)
    region: Mapped[str | None] = mapped_column(String)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RawEnergyRead(Base):
    __tablename__ = "raw_energy_reads"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "external_id", "interval_start", name="ux_energy_ext"
        ),
        {"postgresql_partition_by": "RANGE (interval_start)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, primary_key=True)
    interval_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("connections.id"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    kwh: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    fuel: Mapped[str] = mapped_column(String, nullable=False)  # electricity | gas
    meter_ref: Mapped[str | None] = mapped_column(String)
    grid_intensity: Mapped[float | None] = mapped_column(Numeric(7, 2))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
