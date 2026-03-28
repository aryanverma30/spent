"""
Alembic migration environment.

This file is loaded by the `alembic` CLI when running any migration command.
It sets up:
  - The database URL (read from app settings)
  - The target metadata (all SQLAlchemy models via Base.metadata)
  - Async migration execution (required because we use asyncpg)

You should not need to edit this file unless you change the database URL
format or add a second database.

HOW AUTOGENERATE WORKS:
  When you run `alembic revision --autogenerate`, Alembic:
    1. Connects to the database and reads the current schema
    2. Inspects Base.metadata (all your ORM models)
    3. Generates a migration file with the differences

  For autogenerate to pick up a new model, the model must be imported
  BEFORE `target_metadata` is set. This is done via the wildcard import
  of app.models below.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# ── Alembic Config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── App Imports ───────────────────────────────────────────────────────────────
# Import Base and all models so Alembic can discover the schema.
# Adding a new model? Import it here (or import the module that imports it).
from app.services.db import Base           # noqa: E402
from app.models import transaction         # noqa: E402, F401  (import for side effects)

# ── Target Metadata ───────────────────────────────────────────────────────────
# This tells Alembic which tables to compare against the live database.
target_metadata = Base.metadata

# ── Database URL ──────────────────────────────────────────────────────────────
# Read from app settings so we never hardcode credentials here.
from app.config import settings            # noqa: E402
config.set_main_option("sqlalchemy.url", settings.database_url)


# ── Offline Migrations ────────────────────────────────────────────────────────
# "Offline" means generating SQL without connecting to the database.
# Useful for reviewing migrations before running them.

def run_migrations_offline() -> None:
    """Run migrations in offline mode (generate SQL, don't execute)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online Migrations (Async) ─────────────────────────────────────────────────
# "Online" means connecting to the database and applying changes.
# We use NullPool because Alembic runs as a short-lived script, not a server.

def do_run_migrations(connection: Connection) -> None:
    """Execute migrations synchronously on an open connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations within it."""
    connectable = create_async_engine(
        settings.database_url,
        poolclass=pool.NullPool,   # no persistent pool — Alembic runs once and exits
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — wraps the async runner."""
    asyncio.run(run_async_migrations())


# ── Execute ───────────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
