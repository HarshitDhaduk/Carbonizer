"""Data-source connections (bank / telematics / meter) — docs/DB-SCHEMA.md §4."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import ConnStatus, ProviderKind


class Connection(Base, TimestampMixin):
    __tablename__ = "connections"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "provider", "external_account_ref", name="uq_conn_account"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[ProviderKind] = mapped_column(nullable=False)
    status: Mapped[ConnStatus] = mapped_column(
        default=ConnStatus.disconnected, nullable=False
    )
    external_account_ref: Mapped[str | None] = mapped_column(String)
    # envelope-encrypted provider token (never store plaintext)
    access_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
