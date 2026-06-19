"""Shared schema base. Emits camelCase JSON to match the TS client types
(frontend/src/lib/types.ts). FastAPI serializes response models by alias by default.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def to_camel(snake: str) -> str:
    """snake_case → camelCase, matching the TS client keys exactly.

    Note: we do NOT use pydantic's built-in `to_camel`, which relies on
    `str.title()` and capitalizes the letter after a digit
    (`total_tco2e` → `totalTco2E`). The frontend types use `totalTco2e`, so we
    only upper-case the first letter of each underscore segment.
    """
    head, *rest = snake.split("_")
    return head + "".join(word[:1].upper() + word[1:] for word in rest)


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class Problem(CamelModel):
    """RFC 9457-style error body (subset)."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    request_id: str | None = None
