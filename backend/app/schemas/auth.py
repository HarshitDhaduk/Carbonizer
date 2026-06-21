"""Auth schemas."""

from __future__ import annotations

from pydantic import Field, model_validator

from app.schemas.common import CamelModel

# Top of an HIBP-style "you should never use this" list. Catches the lowest-
# effort credential-stuffing attempts without bundling a 600 KB Bloom filter
# (Phase 2.5; the full HIBP integration is a follow-up). Lowercased on check.
_WEAK_PASSWORDS: frozenset[str] = frozenset(
    {
        "password",
        "password1",
        "password123",
        "qwerty",
        "qwerty123",
        "12345678",
        "123456789",
        "1234567890",
        "letmein",
        "welcome",
        "welcome1",
        "abc123456",
        "admin",
        "administrator",
        "iloveyou",
        "monkey123",
        "carbonizer",
        "carbonizer123",
    }
)


class RegisterRequest(CamelModel):
    """`POST /auth/register` body. 12-char password floor + weak-list check
    enforced in the validator below."""

    email: str
    # 12-char minimum follows current NIST 800-63B guidance (length over
    # complexity rules).
    password: str = Field(min_length=12, max_length=128)
    region: str = "GB"

    @model_validator(mode="after")
    def _validate_password(self) -> RegisterRequest:
        pw_lower = self.password.lower()
        email_local = self.email.split("@", 1)[0].lower() if "@" in self.email else ""

        # A weak password isn't just an exact match — `password123!` should be
        # rejected just as much as `password123`. Check substring containment
        # against meaningful weak roots.
        if any(weak in pw_lower for weak in _WEAK_PASSWORDS):
            raise ValueError("That password is on the public breach list — pick another.")
        if email_local and email_local in pw_lower and len(email_local) >= 4:
            raise ValueError("Password can't contain your email address.")
        if self.password.isdigit() or self.password.isalpha():
            raise ValueError(
                "Mix letters and digits — pure-letter or pure-digit "
                "passwords are easy to guess."
            )
        return self


class TokenResponse(CamelModel):
    """Auth response body — back-compat for non-cookie clients (SPA uses cookies)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(CamelModel):
    """Public profile of the signed-in user (returned by ``GET /auth/me``)."""
    id: str
    email: str
    region: str
    target_tco2e: float | None = None
