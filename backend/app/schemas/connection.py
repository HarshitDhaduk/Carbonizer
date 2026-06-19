"""Connection schemas — mirror the frontend DataConnection type.

Note the status uses hyphenated `needs-attention` to match the TS literal union,
distinct from the DB enum's `needs_attention`.
"""

from __future__ import annotations

from typing import Literal

from app.schemas.common import CamelModel
from app.schemas.footprint import FootprintSummary

ConnectionId = Literal["bank", "telematics", "meter"]
ConnectionStatus = Literal[
    "disconnected", "connecting", "connected", "needs-attention"
]


class DataConnection(CamelModel):
    id: ConnectionId
    label: str
    status: ConnectionStatus
    last_sync: str | None = None


class LinkResponse(CamelModel):
    authorize_url: str
    state: str


class ConnectResult(CamelModel):
    """Sandbox connect result for a data source (bank/meter): the connection, how
    many records were imported, and the recomputed footprint (categories upgraded
    to spend- or activity-based)."""

    connection: DataConnection
    records_imported: int
    summary: FootprintSummary
