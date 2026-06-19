"""Pytest fixtures: an httpx AsyncClient bound to the ASGI app (seed mode)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.main import app


async def _seed_mode_db() -> AsyncIterator[AsyncSession | None]:
    """Force seed mode for tests so they don't depend on a live Postgres,
    regardless of USE_DB in .env."""
    yield None


# applies to every test: dashboard services receive db=None → return fixtures
app.dependency_overrides[get_db] = _seed_mode_db


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def api_prefix() -> str:
    return settings.api_v1_prefix


@pytest.fixture
async def auth_headers(client: AsyncClient, api_prefix: str) -> dict[str, str]:
    resp = await client.post(
        f"{api_prefix}/auth/login",
        data={"username": settings.demo_email, "password": settings.demo_password},
    )
    token = resp.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}
