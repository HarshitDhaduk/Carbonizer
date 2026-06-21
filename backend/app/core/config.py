"""Application settings, loaded from environment / .env (Pydantic Settings)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel values that are SAFE in dev but MUST be overridden in production.
# `_assert_no_defaults_in_production` raises at startup if any of these leak
# into a production deploy (Phase 2.3 of docs/IMPROVEMENT-PLAN.md).
DEFAULT_SECRET_KEY = "dev-only-insecure-secret-change-me"
DEFAULT_DEMO_PASSWORD = "demo12345"
DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://carbonizer:carbonizer@localhost:5432/carbonizer"
)


class InsecureProductionConfigError(RuntimeError):
    """Raised at startup if production env vars are still at their dev defaults."""


class Settings(BaseSettings):
    """Process-wide configuration. Loaded once at startup from `.env` +
    environment variables. Hard-fails in production if any dev-default secret
    leaks through (see ``_assert_no_defaults_in_production`` below)."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- app ---
    environment: str = "development"
    project_name: str = "Carbonizer API"
    api_v1_prefix: str = "/api/v1"

    # --- security ---
    secret_key: str = DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    # --- auth cookies (Phase 2.1) ---
    # Names use a `cb_` prefix in dev so the cookie is accepted on http://localhost
    # (the `__Host-` prefix mandates Secure, which we can't honor over plain HTTP).
    # The production deploy can override these to `__Host-access` / `__Host-refresh`
    # / `__Host-csrf` once Secure is on.
    access_cookie_name: str = "cb_access"
    refresh_cookie_name: str = "cb_refresh"
    csrf_cookie_name: str = "cb_csrf"
    # Cookie cross-site policy. In dev (same host: localhost), Lax is the right
    # call — protects against cross-site form-post CSRF without sacrificing
    # the deep-link-from-email use case. In production with the frontend on
    # one origin (Vercel) and the API on another (Render), Lax cookies are
    # NOT sent on cross-site `fetch()`, so login appears to succeed but every
    # subsequent /auth/me 401s. `cookie_samesite` resolves to "none" in prod
    # via the property below; mandates Secure (which prod already has on).
    # State-changing requests are still defended by the CSRF double-submit.
    cookie_samesite_raw: Literal["lax", "strict", "none"] = "lax"
    # Encryption key for envelope-encrypting provider tokens at rest (Phase 2.8).
    # Must be a base64-encoded 32-byte key (Fernet format). Generate with
    # `python -m app.scripts.gen_encryption_key`. Empty string falls back to a
    # deterministic dev-only key.
    encryption_key: str = ""

    # --- CORS ---
    # Stored as a raw comma-separated string (not list[str]) so pydantic-settings
    # doesn't try to JSON-decode the .env value; exposed as a list via the property.
    cors_origins_raw: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias="CORS_ORIGINS",
    )

    # --- database ---
    # When false, the API serves seed data and requires no Postgres (runs anywhere).
    use_db: bool = False
    database_url: str = DEFAULT_DATABASE_URL

    # Connection pool (Phase 4.3). `pool_size` is the steady-state working set
    # per process; `max_overflow` is the burst headroom. `pool_recycle` recycles
    # connections older than ~half an hour to dodge Postgres' default 60 min
    # idle-timeout footgun on Neon's free tier.
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle_s: int = 1800
    # SQL echo for local debugging (extremely chatty — never enable in prod).
    echo_sql: bool = False

    # --- demo credentials (seed mode) ---
    demo_email: str = "demo@carbonizer.app"
    demo_password: str = DEFAULT_DEMO_PASSWORD

    @property
    def cors_origins(self) -> list[str]:
        """Parse the comma-separated CORS_ORIGINS env into a stripped list."""
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        """True when ENVIRONMENT is `production` or `prod` (case-insensitive)."""
        return self.environment.lower() in {"production", "prod"}

    @property
    def cookie_secure(self) -> bool:
        """Mark auth cookies Secure in production (TLS-only). Off in dev so
        cookies are accepted over http://localhost."""
        return self.is_production

    @property
    def cookie_samesite(self) -> Literal["lax", "strict", "none"]:
        """Force SameSite=None in production so the SPA → API cookie auth
        works across deploy hosts (Vercel ↔ Render). `Secure` is also on in
        prod, satisfying the browser's `None`-requires-Secure rule."""
        if self.is_production and self.cookie_samesite_raw == "lax":
            return "none"
        return self.cookie_samesite_raw

    @model_validator(mode="after")
    def _assert_no_defaults_in_production(self) -> Settings:
        """If ENVIRONMENT=production, refuse to start with any default secret in place.

        Prevents the common "forgot to set SECRET_KEY in prod" footgun where all
        JWTs would be signable by anyone who can read the source code.
        """
        if not self.is_production:
            return self
        leaks: list[str] = []
        if self.secret_key == DEFAULT_SECRET_KEY:
            leaks.append("SECRET_KEY")
        if self.demo_password == DEFAULT_DEMO_PASSWORD:
            leaks.append("DEMO_PASSWORD")
        if self.database_url == DEFAULT_DATABASE_URL:
            leaks.append("DATABASE_URL")
        if leaks:
            joined = ", ".join(leaks)
            raise InsecureProductionConfigError(
                f"Refusing to start in production with default values for: {joined}. "
                "Set real values in the environment before deploying."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — re-reading env per request is wasted work."""
    return Settings()


settings = get_settings()
