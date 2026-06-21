"""User, privacy settings, consents, and sessions (docs/DB-SCHEMA.md §3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import LocPrecision


class User(Base, TimestampMixin):
    """A registered account. Argon2id password hash + soft-delete via
    ``deleted_at`` so the audit log can keep historical references."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str] = mapped_column(String(16), nullable=False, default="GB")
    household_size: Mapped[int | None] = mapped_column(Integer)
    income_band: Mapped[str | None] = mapped_column(String(32))
    target_tco2e: Mapped[float | None] = mapped_column(Numeric(6, 2))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    privacy: Mapped[PrivacySettings] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    consents: Mapped[list[Consent]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class PrivacySettings(Base, TimestampMixin):
    """Per-user privacy choices (location precision, retention window, marketing
    opt-in). One row per user; created alongside the User on register."""

    __tablename__ = "privacy_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    location_precision: Mapped[LocPrecision] = mapped_column(
        default=LocPrecision.coarse_1km, nullable=False
    )
    retention_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="privacy")


class Consent(Base, TimestampMixin):
    """Granular consent record — `scope` + `purpose` per provider.
    Auditable via `granted_at` / `withdrawn_at` for GDPR Art. 7."""

    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("connections.id", ondelete="SET NULL")
    )
    scope: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_manager_ref: Mapped[str | None] = mapped_column(String)

    user: Mapped[User] = relationship(back_populates="consents")


class Session(Base, TimestampMixin):
    """Server-side handle for an issued refresh token. Lookup is by token hash
    so a leaked DB row can't replay a session, and revocation is a row-update."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String)
