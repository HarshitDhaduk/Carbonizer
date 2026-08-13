"""Async engine + session factory. Created lazily so the app runs without a DB."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazily create the async engine + sessionmaker on first access."""
    global _engine, _sessionmaker
    if _engine is None:
        # Phase 4.3 tuning. Defaults come from settings so deploys can override
        # via env (Render's free tier has ~95 connection budget; staying under
        # pool_size + max_overflow keeps headroom for Alembic + ad-hoc tools).
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=settings.db_pool_recycle_s,
            echo=settings.echo_sql,
            future=True,
        )
        _sessionmaker = async_sessionmaker(
            _engine, expire_on_commit=False, autoflush=False
        )
    return _engine


async def get_db() -> AsyncIterator[AsyncSession | None]:
    """FastAPI dependency. Yields None in seed mode (USE_DB=false)."""
    if not settings.use_db:
        yield None
        return
    get_engine()
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        yield session


async def dispose_engine() -> None:
    """Close the connection pool — called from the FastAPI lifespan shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        # Clear the sessionmaker too: it holds a reference to the engine we
        # just disposed. Leaving it set means a later get_engine() rebuilds
        # `_engine` but keeps the stale binding, handing out sessions attached
        # to a dead pool.
        _sessionmaker = None
