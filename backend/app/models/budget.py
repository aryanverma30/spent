"""SQLAlchemy ORM model for monthly spending budgets."""
from datetime import datetime

from sqlalchemy import Numeric, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.services.db import Base


class Budget(Base):
    """A monthly spending limit for one category, or for all spending (category="Total")."""

    __tablename__ = "budgets"

    category: Mapped[str] = mapped_column(String(50), primary_key=True)
    monthly_limit: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
