"""
Transaction ORM model.

This file maps the `transactions` database table to a Python class using
SQLAlchemy 2.0's DeclarativeBase pattern. Each attribute on the class
corresponds to a column in the table.

Key SQLAlchemy concepts used here:
  - Mapped[type]     — modern type-annotated column declaration
  - mapped_column()  — column options (primary_key, nullable, default, etc.)
  - Index            — database index for faster queries
  - func.now()       — database-side timestamp (more reliable than Python datetime)
  - uuid4            — generates a random UUID as the primary key

After editing this file, generate and run a migration:
    docker-compose exec backend alembic revision --autogenerate -m "describe change"
    docker-compose exec backend alembic upgrade head
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.services.db import Base


class Transaction(Base):
    """ORM model for the transactions table."""

    __tablename__ = "transactions"

    # ── Primary Key ───────────────────────────────────────────────────────────
    # UUID is safer than integer IDs — it's unguessable and globally unique.
    # default=uuid.uuid4 generates a new UUID in Python before INSERT.

    # TODO: Define the `id` column.
    # Hint:
    #   id: Mapped[uuid.UUID] = mapped_column(
    #       UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    #   )

    # ── Required Fields ───────────────────────────────────────────────────────

    # TODO: Define `amount` — NUMERIC(10,2), not nullable.
    # Hint: use Numeric(10, 2) as the column type.

    # TODO: Define `merchant` — VARCHAR(255), not nullable.
    # Hint: use String(255) as the column type.

    # TODO: Define `category` — VARCHAR(50), not nullable.
    # Hint: use String(50) as the column type.

    # TODO: Define `raw_input` — TEXT, not nullable.
    # Hint: use Text() as the column type.

    # ── Optional Fields ───────────────────────────────────────────────────────

    # TODO: Define `ai_confidence` — FLOAT, nullable.
    # Hint: use Optional[float] as the Mapped type, and nullable=True.

    # TODO: Define `note` — TEXT, nullable.
    # Hint: use Optional[str] as the Mapped type.

    # ── Timestamps ────────────────────────────────────────────────────────────
    # server_default=func.now() sets the value at the DATABASE level on INSERT.
    # onupdate=func.now() updates it at the DATABASE level on UPDATE.
    # Both are more reliable than setting them in Python.

    # TODO: Define `created_at` — TIMESTAMPTZ, not nullable, default NOW().
    # Hint:
    #   created_at: Mapped[datetime] = mapped_column(
    #       nullable=False, server_default=func.now()
    #   )

    # TODO: Define `updated_at` — TIMESTAMPTZ, not nullable, default NOW(), updates on change.
    # Hint: add onupdate=func.now() to mapped_column().

    # ── Indexes ───────────────────────────────────────────────────────────────
    # Indexes speed up queries on frequently filtered/sorted columns.
    # __table_args__ is where SQLAlchemy looks for table-level constraints.

    # TODO: Define __table_args__ with three indexes:
    #   1. Index on created_at DESC  (most recent first — used by GET /transactions)
    #   2. Index on category         (used by GET /transactions?category=food)
    #   3. Composite index on (category, created_at)  (used by summary queries)
    #
    # Hint:
    #   __table_args__ = (
    #       Index("ix_transactions_created_at", "created_at"),
    #       Index("ix_transactions_category", "category"),
    #       Index("ix_transactions_category_created_at", "category", "created_at"),
    #   )

    def __repr__(self) -> str:
        """Human-readable representation for debugging."""
        # TODO: Return a useful string, e.g.:
        #   return f"<Transaction id={self.id} merchant={self.merchant!r} amount={self.amount}>"
        return f"<Transaction>"
