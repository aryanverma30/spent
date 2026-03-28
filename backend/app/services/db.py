"""
Database session setup.

This module provides three things that the rest of the app needs:

  1. `engine`    — the async SQLAlchemy engine (one per process)
  2. `Base`      — the declarative base that all ORM models inherit from
  3. `get_session` — a FastAPI dependency that yields a session per request

How a request uses the database:
    1. FastAPI calls get_session() via Depends(get_session)
    2. get_session opens a new AsyncSession from the session factory
    3. The route handler receives the session and runs queries
    4. When the handler returns, get_session commits (or rolls back on error)
    5. The session is closed automatically

Usage in a route:
    from app.services.db import get_session
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import Depends

    @router.get("/")
    async def list_items(session: AsyncSession = Depends(get_session)):
        result = await session.execute(select(MyModel))
        return result.scalars().all()
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ── Declarative Base ──────────────────────────────────────────────────────────
# All SQLAlchemy ORM models must inherit from this class.
# Alembic uses Base.metadata to discover tables for autogenerate migrations.

class Base(DeclarativeBase):
    """Base class for all ORM models. Import this in every model file."""
    pass


# ── Async Engine ──────────────────────────────────────────────────────────────
# The engine manages the connection pool. Create it once at module load time.
#
# Key parameters to understand:
#   echo       — if True, SQLAlchemy logs every SQL statement (useful for debugging)
#   pool_size  — number of persistent connections kept open
#   max_overflow — extra connections allowed above pool_size under heavy load

engine = create_async_engine(
    # TODO: Add engine configuration kwargs here.
    # Hint — a good starting point for development:
    #   echo=settings.is_development,
    #   pool_size=5,
    #   max_overflow=10,
    #   pool_timeout=30,
    #   pool_recycle=3600,   # recycle connections every hour to avoid stale connections
    settings.database_url,
)


# ── Session Factory ───────────────────────────────────────────────────────────
# async_sessionmaker creates new AsyncSession objects on demand.
# Think of it like a "session blueprint".
#
# Key parameters:
#   expire_on_commit=False — keeps ORM objects usable after session.commit()
#                            Without this, accessing obj.id after commit raises an error.
#   autoflush=False        — don't auto-flush before queries; we control this manually.

async_session_factory = async_sessionmaker(
    # TODO: Add session factory configuration kwargs here.
    # Hint:
    #   bind=engine,
    #   class_=AsyncSession,
    #   expire_on_commit=False,
    #   autoflush=False,
    #   autocommit=False,
)


# ── Session Dependency ────────────────────────────────────────────────────────
# This is a FastAPI dependency. Routes use it like:
#   async def my_route(session: AsyncSession = Depends(get_session)):
#
# The `yield` makes this a context manager — code after yield runs on cleanup.

async def get_session() -> AsyncSession:
    """
    Yield an AsyncSession for use in FastAPI route handlers.

    Automatically commits on success and rolls back on exception.
    The session is always closed when the request finishes.

    TODO: Implement the session lifecycle here.
    Hint — the pattern looks like:
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    """
    # TODO: Replace this placeholder with the real implementation above.
    raise NotImplementedError("get_session() is not yet implemented — see the TODO above.")
