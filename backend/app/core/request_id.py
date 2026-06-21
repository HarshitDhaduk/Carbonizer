"""``X-Request-Id`` propagation middleware (Phase 7 production readiness).

On every request:

  1. Use the inbound ``X-Request-Id`` header if the caller supplied one
     (Render's edge proxy + most load balancers tag a value), otherwise
     mint a fresh UUID4.
  2. Store the value in :data:`app.core.logging.request_id_var` so the
     JSON formatter weaves it into every log line produced by this
     request, across handlers, services, and exception loggers.
  3. Echo the value back on the response so callers can quote it in bug
     reports.

The contextvar token is reset in the ``finally`` block so a worker
recycling a coroutine for the next request starts clean.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

_HEADER = "X-Request-Id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid = request.headers.get(_HEADER) or uuid.uuid4().hex
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers[_HEADER] = rid
        return response
