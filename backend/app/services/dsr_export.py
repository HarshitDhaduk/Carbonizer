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


async def assemble_export_bundle(
    db: AsyncSession, user_id: uuid.UUID
) -> dict[str, Any]:
    """Build the full data export for ``user_id``.

    Pulled from every table holding personal data. Provider access tokens are
    intentionally omitted — the export tells the user *what* is connected,
    not the credential. ``connections`` carries enough metadata for the user
    to know which third party held what.
    """
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        # User vanished between the request and the download; surface an empty
        # bundle rather than a 500.
        return {"user_id": str(user_id), "user": None}

    privacy = (
        await db.execute(
            select(PrivacySettings).where(PrivacySettings.user_id == user_id)
        )
    ).scalar_one_or_none()
    profile = (
        await db.execute(
            select(OnboardingProfile).where(OnboardingProfile.user_id == user_id)
        )
    ).scalar_one_or_none()
    connections = (
        (await db.execute(select(Connection).where(Connection.user_id == user_id)))
        .scalars()
        .all()
    )
    transactions = (
        (
            await db.execute(
                select(RawTransaction).where(RawTransaction.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    trips = (
        (await db.execute(select(RawTrip).where(RawTrip.user_id == user_id)))
        .scalars()
        .all()
    )
    readings = (
        (
            await db.execute(
                select(RawEnergyRead).where(RawEnergyRead.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    ledger = (
        (
            await db.execute(
                select(LedgerEntry).where(LedgerEntry.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    snapshots = (
        (
            await db.execute(
                select(FootprintSnapshot).where(
                    FootprintSnapshot.user_id == user_id
                )
            )
        )
        .scalars()
        .all()
    )

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "region": user.region,
            "target_tco2e": float(user.target_tco2e)
            if user.target_tco2e is not None
            else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "privacy_settings": _dump(privacy),
        "onboarding_profile": _dump(profile),
        "connections": [
            {k: _safe(v) for k, v in _dump(c).items() if k != "access_token_enc"}
            for c in connections
        ],
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
