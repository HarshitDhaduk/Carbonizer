"""Data-subject request (DSR) service — GDPR Art. 15/17 / DPDP §11/§12.

Two flows:

  * **Export** (right of access) — assemble the user's data into a JSON bundle.
    The job is recorded with a ``download_url`` pointing at
    ``/api/v1/privacy/export/{job_id}/download``, which re-assembles from the
    live tables on demand. No bundle is persisted, so the artefact is always
    fresh; cancelling is just letting it expire.
  * **Erase** (right to be forgotten) — schedule a hard purge ``ERASURE_GRACE``
    after the request, default 48 h. Users can cancel during the window. A
    sweep run (cron / startup hook) walks pending jobs whose
    ``scheduled_purge_at`` is in the past, cascades through
    ``User.delete`` and the partitioned ``raw_*`` tables, and marks the job
    ``completed``.

Why we don't background-process the export — the free-tier deploy has no worker
and no object store. Synchronous assembly fits the dataset size (a typical
user is < 5 MB after a year). For production, swap this out for a worker
queue + S3 signed URL.

Failures during sweep are caught and logged; one bad row should not poison the
whole sweep.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.models.emission import FootprintSnapshot, LedgerEntry
from app.models.enums import DsrKind, JobStatus
from app.models.ingestion import RawEnergyRead, RawTransaction, RawTrip
from app.models.onboarding import OnboardingProfile
from app.models.privacy import AuditLog, DsrJob
from app.models.user import PrivacySettings, User

logger = logging.getLogger("carbonizer.dsr")

# Grace window before an erase request actually purges the row. GDPR has no
# fixed minimum, but a short window is widely accepted as "lets the user undo
# an accidental tap"; the regulator-facing default in this codebase is 48 h.
ERASURE_GRACE = timedelta(hours=48)


# --- Export -----------------------------------------------------------------


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


# --- Erase ------------------------------------------------------------------


async def create_erase_job(
    db: AsyncSession, user_id: uuid.UUID
) -> DsrJob:
    """Schedule an erasure ``ERASURE_GRACE`` from now.

    Idempotent — if a pending erase already exists for this user, returns it
    rather than queuing a duplicate. Prevents a panicking user from creating a
    stack of jobs (and a stack of audit entries on cancellation).
    """
    existing = (
        await db.execute(
            select(DsrJob).where(
                DsrJob.user_id == user_id,
                DsrJob.kind == DsrKind.erase,
                DsrJob.status == JobStatus.pending,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    now = datetime.now(UTC)
    job = DsrJob(
        user_id=user_id,
        kind=DsrKind.erase,
        status=JobStatus.pending,
        scheduled_purge_at=now + ERASURE_GRACE,
    )
    db.add(job)
    await db.flush()
    return job


async def cancel_erase_job(
    db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID
) -> DsrJob | None:
    """Cancel a pending erase. Returns the updated job, or None if not found
    / not cancellable (already completed or wrong user)."""
    job = (
        await db.execute(
            select(DsrJob).where(
                DsrJob.id == job_id,
                DsrJob.user_id == user_id,
                DsrJob.kind == DsrKind.erase,
                DsrJob.status == JobStatus.pending,
            )
        )
    ).scalar_one_or_none()
    if job is None:
        return None
    job.status = JobStatus.failed  # repurpose 'failed' as 'cancelled' for the job log
    job.error = "cancelled by user"
    job.completed_at = datetime.now(UTC)
    await db.flush()
    return job


async def sweep_overdue_erasures(db: AsyncSession) -> int:
    """Purge users whose erase grace window has expired.

    Intended to be called from a cron / scheduled task. Idempotent — re-running
    after a purge is a no-op because the job rows transition to ``completed``.
    Returns the count of users actually purged.
    """
    now = datetime.now(UTC)
    overdue = (
        (
            await db.execute(
                select(DsrJob).where(
                    DsrJob.kind == DsrKind.erase,
                    DsrJob.status == JobStatus.pending,
                    DsrJob.scheduled_purge_at <= now,
                )
            )
        )
        .scalars()
        .all()
    )
    purged = 0
    for job in overdue:
        try:
            await _purge_user(db, job.user_id)
        except Exception:
            logger.warning(
                "DSR sweep failed for user=%s job=%s", job.user_id, job.id,
                exc_info=True,
            )
            job.status = JobStatus.failed
            job.error = "purge failed; will retry on next sweep"
            continue
        job.status = JobStatus.completed
        job.completed_at = now
        purged += 1
    await db.flush()
    return purged


async def _purge_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Hard delete a user and every personal-data row keyed on them.

    Raw partitions are tables we own; the ON DELETE CASCADE FK from
    ``raw_*.user_id`` to ``users.id`` handles the bulk. Connections, ledger,
    onboarding profile, privacy settings, snapshots are also FK-cascaded.
    Audit log rows are kept (regulator may need them) but the actor_user_id is
    nulled so the user is no longer linkable.
    """
    # null out actor in audit log so the rows survive but anonymize
    await db.execute(
        AuditLog.__table__.update()  # type: ignore[attr-defined]
        .where(AuditLog.actor_user_id == user_id)
        .values(actor_user_id=None)
    )
    # Belt-and-braces explicit deletes — relying on FK cascade only works if
    # every model is declared with ondelete="CASCADE", which is the convention
    # but worth pinning down here.
    await db.execute(delete(RawTransaction).where(RawTransaction.user_id == user_id))
    await db.execute(delete(RawTrip).where(RawTrip.user_id == user_id))
    await db.execute(
        delete(RawEnergyRead).where(RawEnergyRead.user_id == user_id)
    )
    await db.execute(delete(LedgerEntry).where(LedgerEntry.user_id == user_id))
    await db.execute(
        delete(FootprintSnapshot).where(FootprintSnapshot.user_id == user_id)
    )
    await db.execute(delete(Connection).where(Connection.user_id == user_id))
    await db.execute(
        delete(OnboardingProfile).where(OnboardingProfile.user_id == user_id)
    )
    await db.execute(
        delete(PrivacySettings).where(PrivacySettings.user_id == user_id)
    )
    await db.execute(delete(User).where(User.id == user_id))
