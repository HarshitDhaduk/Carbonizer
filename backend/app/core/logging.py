"""Structured logging — Phase 7 production readiness.

Two halves:

  * **JSON formatter** for the production path: one ndjson record per log
    line so log aggregators (Render's stdout pipe, Logtail, Loki) can index
    on ``level``, ``name``, and ``request_id`` directly.
  * **Human-readable formatter** for local dev (the default when
    ``LOG_FORMAT`` is unset and stdout is a TTY).

Request-id propagation lives in :mod:`app.core.request_id`: it
populates a contextvar from the inbound ``X-Request-Id`` header (or mints
a UUID if absent) and writes the same value back on every response. The
JSON formatter pulls that contextvar into every log line so a single
request's full log trail is correlatable across handlers, services, and
exception loggers.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextvars import ContextVar

# Public so middleware + tests can read / write it directly.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class _JsonFormatter(logging.Formatter):
    """Emits one JSON object per record. Fields chosen to play well with
    log aggregators' default schemas — ``ts``, ``level``, ``name``, ``msg``,
    plus ``request_id`` when present and the exception payload on errors."""

    _BASE_FIELDS = ("name", "module", "funcName", "lineno")

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)
            ),
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        rid = request_id_var.get()
        if rid is not None:
            payload["request_id"] = rid
        for field in self._BASE_FIELDS:
            value = getattr(record, field, None)
            if value not in (None, ""):
                payload[field] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Tolerate non-JSON-serialisable extras by str()-ing them.
        return json.dumps(payload, default=str, ensure_ascii=False)


def _want_json() -> bool:
    """Pick the JSON formatter on production or when explicitly requested."""
    fmt = os.environ.get("LOG_FORMAT", "").lower()
    if fmt == "json":
        return True
    if fmt == "text":
        return False
    # Default heuristic: JSON when stdout isn't a TTY (Render, Docker, CI).
    return not sys.stdout.isatty()


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    if _want_json():
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s :: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
