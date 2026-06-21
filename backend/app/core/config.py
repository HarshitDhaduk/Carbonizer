"""Application settings, loaded from environment / .env (Pydantic Settings)."""

from __future__ import annotations

from functools import lru_cache

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

    # --- demo credentials (seed mode) ---
    demo_email: str = "demo@carbonizer.app"
    demo_password: str = DEFAULT_DEMO_PASSWORD

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

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
    return Settings()


settings = get_settings()
