"""Data-subject request jobs, audit log, idempotency keys (DB-SCHEMA §8)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, uuid_pk
from app.models.enums import DsrKind, JobStatus


class DsrJob(Base):
    """Export / erase request (docs/DESIGN.md §10 — 48-h grace before purge)."""

    __tablename__ = "dsr_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[DsrKind] = mapped_column(nullable=False)
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.pending)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    scheduled_purge_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    download_url: Mapped[str | None] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(String)


class AuditLog(Base):
    """Append-only audit trail — partitioned by month, 1-year retention."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_actor_time", "actor_user_id", "created_at"),
        {"postgresql_partition_by": "RANGE (created_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, primary_key=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String)
    resource_id: Mapped[str | None] = mapped_column(String)
    ip: Mapped[str | None] = mapped_column(INET)
    request_id: Mapped[str | None] = mapped_column(String)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String, primary_key=True)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    response_hash: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
