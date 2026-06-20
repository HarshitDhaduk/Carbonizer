"""Connection endpoints — list data sources and connect/sync/disconnect the
(sandbox) bank and smart meter, running the ingestion → carbon → footprint pipeline."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user, require_user
from app.db.session import get_db
from app.models.connection import Connection
from app.models.enums import ConnStatus, ProviderKind
from app.models.ingestion import RawEnergyRead, RawTransaction
from app.schemas.connection import (
    ConnectionId,
    ConnectResult,
    DataConnection,
)
from app.services import bank_sync, dashboard

router = APIRouter(prefix="/connections", tags=["connections"])

_LABELS = {
    ProviderKind.bank: "Bank",
    ProviderKind.telematics: "Travel",
    ProviderKind.meter: "Home energy",
}
# which sandbox provider kinds are wired end-to-end
_WIRED = {"bank": ProviderKind.bank, "meter": ProviderKind.meter}


def _require_db(db: AsyncSession | None) -> AsyncSession:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connections require the database (set USE_DB=true).",
        )
    return db


def _user_uuid(subject: str) -> uuid.UUID:
    try:
        return uuid.UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        ) from exc


async def _connect_and_sync(
    db: AsyncSession, uid: uuid.UUID, kind: ProviderKind
) -> ConnectResult:
    """Upsert the connection, pull from the sandbox provider, recompute."""
    now = datetime.now(UTC)
    res = await db.execute(
        select(Connection).where(
            Connection.user_id == uid, Connection.provider == kind
        )
    )
    conn = res.scalar_one_or_none()
    if conn is None:
        conn = Connection(user_id=uid, provider=kind)
        db.add(conn)
        await db.flush()  # assign conn.id for the FK on raw_* rows
    conn.status = ConnStatus.connected
    conn.external_account_ref = "sandbox-account"
    conn.last_sync_at = now

    if kind is ProviderKind.bank:
        imported = await bank_sync.sync_bank(db, uid, conn.id)
    else:
        imported = await bank_sync.sync_meter(db, uid, conn.id)
    summary = await bank_sync.recompute_footprint(db, uid)
    await db.commit()

    return ConnectResult(
        connection=DataConnection(
            id=kind.value, label=_LABELS[kind], status="connected",
            last_sync="just now",
        ),
        records_imported=imported,
        summary=summary,
    )


@router.get("", response_model=list[DataConnection])
async def list_connections(
    db: AsyncSession | None = Depends(get_db),
    subject: str | None = Depends(get_optional_user),
) -> list[DataConnection]:
    return await dashboard.get_connections(db, subject)


@router.post("/{provider}/link", response_model=ConnectResult)
async def link_connection(
    provider: ConnectionId,
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> ConnectResult:
    """Connect a sandbox source: create/refresh the connection, import records,
    and recompute the footprint (categories → spend- or activity-based)."""
    if provider not in _WIRED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{provider} ingestion is not wired yet.",
        )
    db = _require_db(db)
    return await _connect_and_sync(db, _user_uuid(subject), _WIRED[provider])


@router.post("/{provider}/sync", response_model=ConnectResult)
async def sync_connection(
    provider: ConnectionId,
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> ConnectResult:
    if provider not in _WIRED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{provider} ingestion is not wired yet.",
        )
    db = _require_db(db)
    uid = _user_uuid(subject)
    kind = _WIRED[provider]
    res = await db.execute(
        select(Connection).where(
            Connection.user_id == uid, Connection.provider == kind
        )
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{provider} not connected"
        )
    return await _connect_and_sync(db, uid, kind)


@router.delete("/{provider}")
async def disconnect(
    provider: ConnectionId,
    subject: str = Depends(require_user),
    db: AsyncSession | None = Depends(get_db),
) -> dict[str, str]:
    """Disconnect a source and purge its raw data (data-rights friendly)."""
    if provider not in _WIRED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{provider} ingestion is not wired yet.",
        )
    db = _require_db(db)
    uid = _user_uuid(subject)
    kind = _WIRED[provider]
    if kind is ProviderKind.bank:
        await db.execute(delete(RawTransaction).where(RawTransaction.user_id == uid))
    else:
        await db.execute(delete(RawEnergyRead).where(RawEnergyRead.user_id == uid))
    await db.execute(
        delete(Connection).where(
            Connection.user_id == uid, Connection.provider == kind
        )
    )
    await db.commit()
    return {"status": "disconnected", "provider": provider}
