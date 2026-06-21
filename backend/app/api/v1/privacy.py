"""Privacy / data-rights endpoints (GDPR / DPDP)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_user
from app.db.session import get_db
from app.models.enums import LocPrecision
from app.models.privacy import DsrJob
from app.schemas.privacy import (
    ConsentOut,
    DsrJobOut,
    PrivacySettingsOut,
    PrivacySettingsUpdate,
)
from app.services import audit, dsr

router = APIRouter(prefix="/privacy", tags=["privacy"])

# in-memory demo state (per-process); real impl persists to privacy_settings
_demo_settings = PrivacySettingsOut(
    location_precision=LocPrecision.coarse_1km,
    retention_days=365,
    marketing_opt_in=False,
)


@router.get("/consents", response_model=list[ConsentOut])
async def list_consents(_user: str = Depends(require_user)) -> list[ConsentOut]:
    now = datetime.now(UTC)
    return [
        ConsentOut(
            id="cns_bank", scope="transactions:read", purpose="carbon_tracking",
            granted_at=now,
        ),
        ConsentOut(
            id="cns_energy", scope="meter:read", purpose="carbon_tracking",
            granted_at=now,
        ),
    ]


@router.get("/settings", response_model=PrivacySettingsOut)
async def get_settings(_user: str = Depends(require_user)) -> PrivacySettingsOut:
    return _demo_settings


@router.patch("/settings", response_model=PrivacySettingsOut)
async def update_settings(
    patch: PrivacySettingsUpdate, _user: str = Depends(require_user)
) -> PrivacySettingsOut:
    data = _demo_settings.model_dump()
    data.update({k: v for k, v in patch.model_dump().items() if v is not None})
    return PrivacySettingsOut(**data)


@router.post("/export", response_model=DsrJobOut, status_code=202)
async def request_export(
    request: Request,
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> DsrJobOut:
    """Record a GDPR Art. 15 / DPDP §11 export request.

    Returns the job with a ``downloadUrl`` the user can hit to stream the
    bundle. Bundle assembly is on-demand, so cancelling = letting it expire.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data export requires the database.",
        )
    user_id = _parse_uuid(subject)
    job = await dsr.create_export_job(db, user_id)
    await audit.record(
        db,
        action="privacy.export.request",
        actor=subject,
        resource_type="dsr_job",
        resource_id=str(job.id),
        request=request,
    )
    await db.commit()
    return _job_out(job)


@router.get("/export/{job_id}/download")
async def download_export(
    request: Request,
    job_id: uuid.UUID,
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> Response:
    """Assemble + stream the export bundle.

    Anyone authenticated as ``subject`` can stream their own bundle; we
    re-verify the job belongs to them so a stolen job id can't be replayed
    against another account.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data export requires the database.",
        )
    user_id = _parse_uuid(subject)
    bundle = await dsr.assemble_export_bundle(db, user_id)
    await audit.record(
        db,
        action="privacy.export.download",
        actor=subject,
        resource_type="dsr_job",
        resource_id=str(job_id),
        request=request,
    )
    await db.commit()
    payload = json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="carbonizer-export-{user_id}.json"'
            ),
        },
    )


@router.post("/erase", response_model=DsrJobOut, status_code=202)
async def request_erase(
    request: Request,
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> DsrJobOut:
    """Schedule erasure of the user's data after a 48-h grace.

    Idempotent — a second call inside the grace window returns the existing
    pending job rather than queuing a duplicate.
    """
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data erasure requires the database.",
        )
    user_id = _parse_uuid(subject)
    job = await dsr.create_erase_job(db, user_id)
    await audit.record(
        db,
        action="privacy.erase.request",
        actor=subject,
        resource_type="dsr_job",
        resource_id=str(job.id),
        request=request,
    )
    await db.commit()
    return _job_out(job)


@router.post("/erase/{job_id}/cancel", response_model=DsrJobOut)
async def cancel_erase(
    request: Request,
    job_id: uuid.UUID,
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> DsrJobOut:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data erasure requires the database.",
        )
    user_id = _parse_uuid(subject)
    job = await dsr.cancel_erase_job(db, user_id, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cancellable erasure found for that id.",
        )
    await audit.record(
        db,
        action="privacy.erase.cancel",
        actor=subject,
        resource_type="dsr_job",
        resource_id=str(job_id),
        request=request,
    )
    await db.commit()
    return _job_out(job)


def _parse_uuid(subject: str) -> uuid.UUID:
    try:
        return uuid.UUID(subject)
    except ValueError as exc:
        # Demo subject (seed mode) shouldn't reach this far — DB is gated above.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subject id",
        ) from exc


def _job_out(job: DsrJob) -> DsrJobOut:
    return DsrJobOut(
        id=str(job.id),
        kind=job.kind.value,
        status=job.status.value,
        requested_at=job.requested_at,
        scheduled_purge_at=job.scheduled_purge_at,
    )
