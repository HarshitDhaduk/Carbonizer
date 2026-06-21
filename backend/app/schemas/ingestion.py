"""Ingestion payloads (provider webhooks / edge oracle)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.enums import TripMode
from app.schemas.common import CamelModel


class TransactionIn(CamelModel):
    """One bank transaction posted to ``/ingest/transactions``."""

    external_id: str
    booked_at: datetime
    amount_minor: int
    currency: str
    mcc: str | None = None
    description: str | None = None
    merchant: str | None = None
    spend_region: str | None = None


class TripIn(CamelModel):
    """One detected trip posted to ``/ingest/trips`` (telematics SDK)."""

    external_id: str
    started_at: datetime
    ended_at: datetime
    mode: TripMode
    distance_m: int
    region: str | None = None


class EnergyReadIn(CamelModel):
    """One smart-meter reading posted to ``/ingest/energy``."""

    external_id: str
    interval_start: datetime
    kwh: float
    fuel: str
    meter_ref: str | None = None


class IngestResult(CamelModel):
    """Async-ingest ack: count accepted, count deduped, and any rejected ids."""

    accepted: int
    duplicates: int = 0
    rejected: list[str] = Field(default_factory=list)
