"""Privacy / data-rights schemas (GDPR / DPDP)."""

from __future__ import annotations

from datetime import datetime

from app.models.enums import LocPrecision
from app.schemas.common import CamelModel


class ConsentOut(CamelModel):
    id: str
    scope: str
    purpose: str
    granted_at: datetime | None = None
    withdrawn_at: datetime | None = None


class PrivacySettingsOut(CamelModel):
    location_precision: LocPrecision
    retention_days: int
    marketing_opt_in: bool


class PrivacySettingsUpdate(CamelModel):
    location_precision: LocPrecision | None = None
    retention_days: int | None = None
    marketing_opt_in: bool | None = None


class DsrJobOut(CamelModel):
    id: str
    kind: str
    status: str
    requested_at: datetime
    scheduled_purge_at: datetime | None = None
