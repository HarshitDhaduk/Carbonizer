"""Recommendation (nudge) schemas — mirror the frontend Nudge type."""

from __future__ import annotations

from datetime import datetime

from app.models.enums import NudgeEffort, NudgeKind
from app.schemas.common import CamelModel


class Nudge(CamelModel):
    id: str
    kind: NudgeKind
    title: str
    detail: str
    carbon_saved_tco2e: float
    money_saved: float
    currency: str
    effort: NudgeEffort
    window_ends_at: datetime | None = None


class NudgeActionResult(CamelModel):
    id: str
    status: str
    realized_saving_tco2e: float | None = None
