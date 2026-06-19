"""Privacy / data-rights endpoints (GDPR / DPDP). Stubs over the real workflows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.api.deps import require_user
from app.models.enums import LocPrecision
from app.schemas.privacy import (
    ConsentOut,
    DsrJobOut,
    PrivacySettingsOut,
    PrivacySettingsUpdate,
)

router = APIRouter(prefix="/privacy", tags=["privacy"])

# in-memory demo state (per-process); real impl persists to privacy_settings
_demo_settings = PrivacySettingsOut(
    location_precision=LocPrecision.coarse_1km,
    retention_days=365,
    marketing_opt_in=False,
)


@router.get("/consents", response_model=list[ConsentOut])
async def list_consents(_user: str = Depends(require_user)) -> list[ConsentOut]:
    now = datetime.now(timezone.utc)
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
async def request_export(_user: str = Depends(require_user)) -> DsrJobOut:
    return DsrJobOut(
        id="dsr_export_demo",
        kind="export",
        status="pending",
        requested_at=datetime.now(timezone.utc),
    )


@router.post("/erase", response_model=DsrJobOut, status_code=202)
async def request_erase(_user: str = Depends(require_user)) -> DsrJobOut:
    now = datetime.now(timezone.utc)
    return DsrJobOut(
        id="dsr_erase_demo",
        kind="erase",
        status="pending",
        requested_at=now,
        scheduled_purge_at=now + timedelta(hours=48),  # docs/DESIGN.md §10
    )
