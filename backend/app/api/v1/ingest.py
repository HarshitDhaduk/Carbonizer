"""Ingestion endpoints (provider webhooks / edge oracle).

These accept payloads and acknowledge; the classification + emission-factor
pipeline that writes ledger_entries runs asynchronously (DB-SCHEMA §4–5). The
handlers are no-ops today — the live path is ``services.bank_sync``, driven by
``/connections/{provider}/sync``.

**Not yet authenticated.** Production needs an HMAC signature header and a
bounded batch size; neither is implemented, so today an anonymous caller can
force an arbitrarily large Pydantic parse. Both changes alter the contract for
existing callers, so they're tracked as follow-ups rather than bolted on — see
docs/AUDIT-2026-08.md (L5). Do not route real provider traffic here until they
land.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.ingestion import (
    EnergyReadIn,
    IngestResult,
    TransactionIn,
    TripIn,
)

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "/transactions",
    response_model=IngestResult,
    status_code=202,
    summary="Accept bank-transaction batch from a provider webhook",
)
async def ingest_transactions(items: list[TransactionIn]) -> IngestResult:
    """Accept + ack the batch. Dedup, classify, and factor-mapping happen
    asynchronously downstream (see ``services.bank_sync``)."""
    return IngestResult(accepted=len(items))


@router.post(
    "/trips",
    response_model=IngestResult,
    status_code=202,
    summary="Accept telematics-trip batch from a provider webhook",
)
async def ingest_trips(items: list[TripIn]) -> IngestResult:
    """Accept + ack the trip batch; mode-detection + km-to-CO2e is async."""
    return IngestResult(accepted=len(items))


@router.post(
    "/energy",
    response_model=IngestResult,
    status_code=202,
    summary="Accept smart-meter energy-read batch from a provider webhook",
)
async def ingest_energy(items: list[EnergyReadIn]) -> IngestResult:
    """Accept + ack the energy batch; the activity-vs-grid-intensity merge is async."""
    return IngestResult(accepted=len(items))
