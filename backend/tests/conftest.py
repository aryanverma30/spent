"""pytest configuration and shared fixtures for the Spent test suite.

Uses an in-memory SQLite database (via aiosqlite) so no running PostgreSQL
instance is required.  gen_random_uuid() is registered as a SQLite UDF so
the server_default on Transaction.id compiles successfully.
"""
import os
import uuid

# Must be set before any app imports so pydantic-settings reads them.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.services.db import Base, get_session

# ---------------------------------------------------------------------------
# Test engine — in-memory SQLite shared across all connections in a session
# ---------------------------------------------------------------------------

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine.sync_engine, "connect")
def _register_sqlite_udf(dbapi_conn, _record) -> None:
    """Register gen_random_uuid() so PostgreSQL server_defaults work on SQLite."""
    dbapi_conn.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))


_TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# Session dependency override
# ---------------------------------------------------------------------------


async def _override_get_session():
    """FastAPI dependency override that provides a test SQLite session."""
    async with _TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_tables():
    """Create all tables once for the test session, drop them at teardown."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    """Truncate every table between tests so state does not leak."""
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Provide a raw AsyncSession pointed at the test database."""
    async with _TestSessionFactory() as s:
        yield s


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Provide an httpx.AsyncClient wired to the FastAPI app with the test DB."""
    app.dependency_overrides[get_session] = _override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
