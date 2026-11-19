"""Async SQLAlchemy 2.0 engine + session management.

Uses the repo's seeded SQLite DB by default (aiosqlite). FK enforcement is OFF
by default per SQLite connection, so we turn it ON for every connection — the
canonical schema relies on it (see _DB/README.md).
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.db")

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _create_engine() -> AsyncEngine:
    url = settings.effective_database_url
    connect_args: dict = {}
    if settings.is_sqlite:
        connect_args = {"timeout": 30}
    engine = create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    if settings.is_sqlite:
        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute("PRAGMA busy_timeout = 5000;")
            cur.close()

    logger.info("db_engine_created", extra={"url": _safe_url(url)})
    return engine


def _safe_url(url: str) -> str:
    # Avoid logging credentials for non-sqlite URLs.
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        if "@" in rest:
            return f"{scheme}://***@{rest.split('@', 1)[1]}"
    return url


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        _engine = _create_engine()
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, rolls back on error, always closes."""
    maker = get_sessionmaker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def ping() -> bool:
    """Lightweight DB health probe."""
    try:
        maker = get_sessionmaker()
        async with maker() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:  # pragma: no cover - exercised via health endpoint
        logger.exception("db_ping_failed")
        return False


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _sessionmaker = None
