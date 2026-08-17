"""Audit log writer (Phase 2.6, docs/IMPROVEMENT-PLAN.md).

Append-only record of security-relevant actions: auth events (login / register /
me-failed), connection link/disconnect, privacy DSR requests. The `audit_log`
table is partitioned by month with a 1-year retention target (DB-SCHEMA §10).

Failure to write an audit row never crashes the request — auditing is best-effort
and observability-only. The `record` helper logs at WARNING level if the write
fails so anomalies are still surfaced.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import request_id_var
from app.models.privacy import AuditLog

logger = logging.getLogger("carbonizer.audit")


def _maybe_uuid(value: str | None) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        return None


async def record(
    db: AsyncSession | None,
    *,
    action: str,
    actor: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    request: Request | None = None,
) -> None:
    """Best-effort audit row insert. Never raises.

    Args:
        db: Active session, or None in seed mode (no-op).
        action: Verb + noun, e.g. ``auth.login.success``, ``auth.register.success``,
                ``connection.link``, ``privacy.export.request``.
        actor: User UUID (string) or None for unauthenticated events.
        resource_type / resource_id: What the action targeted (e.g.
                ``connection`` / ``<conn-uuid>``).
        request: Optional FastAPI request — its client IP and request id are
                captured if available.
    """
    if db is None:
        return  # seed mode — nothing to write
    ip = request.client.host if request and request.client else None
    # Contextvar first: RequestIdMiddleware mints a UUID when the caller sends
    # no X-Request-Id and stores it there, but never writes it back onto the
    # request headers. Reading the header alone left request_id NULL on every
    # direct call while the logs and the response header carried an id —
    # exactly the correlation this table exists for.
    req_id = request_id_var.get()
    if req_id is None and request is not None:
        req_id = request.headers.get("x-request-id")
    try:
        db.add(
            AuditLog(
                actor_user_id=_maybe_uuid(actor),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip=ip,
                request_id=req_id,
            )
        )
        await db.flush()
    except Exception:
        logger.warning("audit log write failed for action=%s", action, exc_info=True)
