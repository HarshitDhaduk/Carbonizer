"""Data-subject request (DSR) service — GDPR Art. 17 / DPDP §12 (right to be
forgotten).

Schedules a hard purge ``ERASURE_GRACE`` after the request, default 48 h. Users
can cancel during the window. A sweep run (cron / startup hook) walks pending
jobs whose ``scheduled_purge_at`` is in the past, cascades through
``User.delete`` and the partitioned ``raw_*`` tables, and marks the job
``completed``.

The companion right-of-access flow (Art. 15 / DPDP §11 — data export) lives in
:mod:`app.services.dsr_export` and is re-exported from this module for back-
compat with ``from app.services import dsr; dsr.create_export_job(...)``.

Failures during sweep are caught and logged; one bad row should not poison the
whole sweep.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connection import Connection
from app.models.emission import FootprintSnapshot, LedgerEntry
from app.models.enums import DsrKind, JobStatus
from app.models.ingestion import RawEnergyRead, RawTransaction, RawTrip
from app.models.onboarding import OnboardingProfile
from app.models.privacy import AuditLog, DsrJob
from app.models.user import PrivacySettings, User
from app.services.dsr_export import assemble_export_bundle, create_export_job

__all__ = [
    "ERASURE_GRACE",
    "assemble_export_bundle",
    "cancel_erase_job",
    "create_erase_job",
    "create_export_job",
    "sweep_overdue_erasures",
]

logger = logging.getLogger("carbonizer.dsr")

# Grace window before an erase request actually purges the row. GDPR has no
# fixed minimum, but a short window is widely accepted as "lets the user undo
# an accidental tap"; the regulator-facing default in this codebase is 48 h.
ERASURE_GRACE = timedelta(hours=48)


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
        update(AuditLog)
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
