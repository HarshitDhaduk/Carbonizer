"""Auth schemas."""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import CamelModel


class RegisterRequest(CamelModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    region: str = "GB"


class TokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(CamelModel):
    id: str
    email: str
    region: str
    target_tco2e: float | None = None
