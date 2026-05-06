"""SQLAlchemy ORM model for learned merchant-to-category mappings."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.services.db import Base


class MerchantOverride(Base):
    """Stores user-corrected merchant-to-category mappings for NLP learning."""

    __tablename__ = "merchant_overrides"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    merchant_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    last_used_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
