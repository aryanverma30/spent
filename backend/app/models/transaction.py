"""SQLAlchemy ORM model for the transactions table."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Float, Numeric, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.services.db import Base


class Transaction(Base):
    """Represents a single financial transaction."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    merchant: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_transactions_created_at", "created_at"),
        Index("ix_transactions_category", "category"),
        Index("ix_transactions_category_created_at", "category", "created_at"),
    )

    def __repr__(self) -> str:
        """Return a debug-friendly representation."""
        return f"<Transaction id={self.id} merchant={self.merchant!r} amount={self.amount}>"
