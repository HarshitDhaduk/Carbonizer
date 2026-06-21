"""Data-source connections (bank / telematics / meter) — docs/DB-SCHEMA.md §4.

The provider access token is envelope-encrypted at rest (Phase 2.8). The raw
column is ``access_token_enc`` (LargeBinary); callers go through
:func:`set_access_token` / :func:`get_access_token`, which transparently apply
Fernet via :mod:`app.core.crypto`. Direct assignment to ``access_token_enc``
is reserved for migration / re-encryption tooling.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import decrypt, encrypt
from app.db.base import Base, TimestampMixin, uuid_pk
from app.models.enums import ConnStatus, ProviderKind


class Connection(Base, TimestampMixin):
    """A user's link to a single provider account (bank/telematics/meter).
    Unique on (user, provider, external_account_ref) so reconnecting the same
    account upserts rather than duplicates."""

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
    # envelope-encrypted provider token (never store plaintext); see set_access_token
    access_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


def set_access_token(conn: Connection, plaintext: str | None) -> None:
    """Encrypt ``plaintext`` and stash it on the connection.

    Passing ``None`` clears the token (used by ``/connections/{provider}/sync``
    when a provider revokes and we want the row to survive but un-authenticated).
    """
    conn.access_token_enc = encrypt(plaintext) if plaintext else None


def get_access_token(conn: Connection) -> str | None:
    """Decrypt the stored token, or None if not set.

    Raises :class:`cryptography.fernet.InvalidToken` if the row was encrypted
    with a different key — by surfacing it (rather than swallowing) we make a
    key-rotation mistake loud.
    """
    return decrypt(conn.access_token_enc)
