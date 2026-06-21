"""GDPR Art. 15 / DPDP §11 — data-export job + bundle assembly.

The job row is recorded with a ``download_url`` pointing at
``/api/v1/privacy/export/{job_id}/download``, which re-assembles from the
live tables on demand. No bundle is persisted, so the artefact is always
fresh; cancelling is just letting it expire.

Why we don't background-process the export — the free-tier deploy has no
worker and no object store. Synchronous assembly fits the dataset size (a
typical user is < 5 MB after a year). For production, swap this out for a
worker queue + S3 signed URL.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.models.emission import FootprintSnapshot, LedgerEntry
from app.models.enums import DsrKind, JobStatus
from app.models.ingestion import RawEnergyRead, RawTransaction, RawTrip
from app.models.onboarding import OnboardingProfile
from app.models.privacy import DsrJob
from app.models.user import PrivacySettings, User


async def create_export_job(db: AsyncSession, user_id: uuid.UUID) -> DsrJob:
    """Record an export request. Bundle is assembled on download, not now."""
    job = DsrJob(
        user_id=user_id,
        kind=DsrKind.export,
        status=JobStatus.completed,
        download_url="/api/v1/privacy/export/{job_id}/download",
        completed_at=datetime.now(UTC),
    )
    db.add(job)
    await db.flush()
    # Self-reference the row id so the URL actually resolves.
    job.download_url = f"/api/v1/privacy/export/{job.id}/download"
    return job


async def _fetch_one(
    db: AsyncSession, model: Any, user_id: uuid.UUID
) -> object | None:
    """Return the single user-scoped row of ``model``, if any."""
    result: Any = await db.execute(select(model).where(model.user_id == user_id))
    row: object | None = result.scalar_one_or_none()
    return row


async def _fetch_many(
    db: AsyncSession, model: Any, user_id: uuid.UUID
) -> list[object]:
    """Return every user-scoped row of ``model`` (raw_* and ledger tables)."""
    result: Any = await db.execute(select(model).where(model.user_id == user_id))
    return list(result.scalars().all())


def _user_section(user: User) -> dict[str, Any]:
    """User profile fields shaped for the export bundle."""
    return {
        "id": str(user.id),
        "email": user.email,
        "region": user.region,
        "target_tco2e": (
            float(user.target_tco2e) if user.target_tco2e is not None else None
        ),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _connection_row(conn: object) -> dict[str, Any]:
    """A single Connection row with the encrypted access token redacted."""
    return {k: _safe(v) for k, v in _dump(conn).items() if k != "access_token_enc"}


async def assemble_export_bundle(
    db: AsyncSession, user_id: uuid.UUID
) -> dict[str, Any]:
    """Build the full data export for ``user_id``.

    Pulled from every table holding personal data. Provider access tokens are
    intentionally omitted — the export tells the user *what* is connected,
    not the credential.
    """
    user_obj = await _fetch_one(db, User, user_id)
    if not isinstance(user_obj, User):
        # User vanished between the request and the download; surface an empty
        # bundle rather than a 500. (isinstance also narrows the type for mypy
        # so the _user_section call below doesn't need a `cast` or ignore.)
        return {"user_id": str(user_id), "user": None}

    privacy = await _fetch_one(db, PrivacySettings, user_id)
    profile = await _fetch_one(db, OnboardingProfile, user_id)
    connections = await _fetch_many(db, Connection, user_id)
    transactions = await _fetch_many(db, RawTransaction, user_id)
    trips = await _fetch_many(db, RawTrip, user_id)
    readings = await _fetch_many(db, RawEnergyRead, user_id)
    ledger = await _fetch_many(db, LedgerEntry, user_id)
    snapshots = await _fetch_many(db, FootprintSnapshot, user_id)

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "user": _user_section(user_obj),
        "privacy_settings": _dump(privacy),
        "onboarding_profile": _dump(profile),
        "connections": [_connection_row(c) for c in connections],
        "raw_transactions": [_dump(t) for t in transactions],
        "raw_trips": [_dump(t) for t in trips],
        "raw_energy_readings": [_dump(r) for r in readings],
        "ledger_entries": [_dump(le) for le in ledger],
        "footprint_snapshots": [_dump(s) for s in snapshots],
    }


def _dump(obj: object | None) -> dict[str, Any]:
    if obj is None:
        return {}
    cols = getattr(obj.__class__, "__table__", None)
    if cols is None:
        return {}
    return {c.name: _safe(getattr(obj, c.name, None)) for c in cols.columns}


def _safe(value: Any) -> Any:
    """JSON-safe coercion for ORM column values."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        return None  # ciphertext is not part of the export
    if hasattr(value, "value") and hasattr(value, "name"):  # enum
        return value.value
    return value
