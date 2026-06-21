"""Liveness / readiness probes.

Two separate signals, following the kubernetes convention:

  * **`/healthz`** — process-alive check. Cheap, never touches I/O. The
    container orchestrator restarts on persistent failure here.
  * **`/readyz`** — backing-service check. Pings the DB; returns 503 if the
    pool can't service a `SELECT 1`. The orchestrator pulls the pod out of
    rotation on persistent failure here without restarting it.

Render's "Health Check Path" should point at `/readyz` in production so a
DB blip drains traffic from this instance.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_engine

router = APIRouter(tags=["health"])


@router.get(
    "/healthz",
    summary="Liveness probe (process alive)",
    description="Cheap, no I/O. Returns 200 as long as the ASGI app is serving.",
)
async def healthz() -> dict[str, str]:
    """Liveness probe — returns 200 + `status=ok` while the ASGI app is serving."""
    return {"status": "ok"}


@router.get(
    "/readyz",
    summary="Readiness probe (backing services healthy)",
    description=(
        "Pings the DB with `SELECT 1`. Returns 200 + JSON describing the "
        "checks on success; 503 + the same JSON on any failure so traffic "
        "drains from this instance. In seed mode (`USE_DB=false`) the DB "
        "check is skipped — useful for local dev, never the production deploy."
    ),
)
async def readyz(response: Response) -> dict[str, object]:
    """Readiness probe — pings DB with `SELECT 1`; 503 on any failure."""
    db_ok: bool | str = "skipped"
    if settings.use_db:
        try:
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception as exc:
            db_ok = f"error: {exc}"

    healthy = db_ok is True or db_ok == "skipped"
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if healthy else "degraded", "database": db_ok}
