"""Pytest fixtures: an httpx AsyncClient bound to the ASGI app (seed mode)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.main import app


async def _seed_mode_db() -> AsyncIterator[AsyncSession | None]:
    """Force seed mode for tests so they don't depend on a live Postgres,
    regardless of USE_DB in .env."""
    yield None


# applies to every test: dashboard services receive db=None → return fixtures
app.dependency_overrides[get_db] = _seed_mode_db

# slowapi treats every test as the same client (`testclient` IP), so the
# /auth/login fixture would burn through "5/minute" after a handful of tests.
# Disable rate limiting for the whole suite; tests that need to verify the
# limiter explicitly re-enable it via the `with_rate_limit` fixture below.
limiter.enabled = False


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def api_prefix() -> str:
    return settings.api_v1_prefix


@pytest.fixture
def with_rate_limit() -> AsyncIterator[None]:  # type: ignore[misc]
    """Re-enable slowapi inside a test that needs to exercise the limiter."""
    limiter.reset()
    limiter.enabled = True
    try:
        yield
    finally:
        limiter.enabled = False
        limiter.reset()


@pytest.fixture
async def auth_headers(client: AsyncClient, api_prefix: str) -> dict[str, str]:
    resp = await client.post(
        f"{api_prefix}/auth/login",
        data={"username": settings.demo_email, "password": settings.demo_password},
    )
    token = resp.json()["accessToken"]
    # Login also sets HttpOnly auth cookies on the httpx CookieJar; wipe them
    # so tests that pass `headers=auth_headers` exercise the Bearer-auth path
    # cleanly without tripping CSRF on the cookie path.
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}
