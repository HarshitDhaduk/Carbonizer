"""Ingestion endpoints (provider webhooks / edge oracle).

Authenticated machine-to-machine in production (HMAC signature header). Here they
accept payloads and acknowledge; the classification + emission-factor pipeline that
writes ledger_entries runs asynchronously (DB-SCHEMA §4–5).
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


@router.post("/transactions", response_model=IngestResult, status_code=202)
async def ingest_transactions(items: list[TransactionIn]) -> IngestResult:
    # TODO: dedup on (user, external_id), classify, enqueue factor mapping
    return IngestResult(accepted=len(items))


@router.post("/trips", response_model=IngestResult, status_code=202)
async def ingest_trips(items: list[TripIn]) -> IngestResult:
    return IngestResult(accepted=len(items))


@router.post("/energy", response_model=IngestResult, status_code=202)
async def ingest_energy(items: list[EnergyReadIn]) -> IngestResult:
    return IngestResult(accepted=len(items))
