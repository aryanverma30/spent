"""Pydantic v2 schemas for request validation and response serialization."""
import uuid
from datetime import datetime
import re
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import CATEGORIES, LOCAL_TZ


def validate_category(value: str | None) -> str | None:
    """Reject category names that aren't in the shared CATEGORIES list."""
    if value is not None and value not in CATEGORIES:
        raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
    return value


def localize(value: datetime | None) -> datetime | None:
    """Treat naive timestamps (e.g. a bare "2026-09-29" date) as local time."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=LOCAL_TZ)
    return value


class TransactionPatch(BaseModel):
    """Schema for partially updating a transaction (PATCH)."""

    category: Optional[str] = Field(None, max_length=50)
    note: Optional[str] = None
    occurred_at: Optional[datetime] = None

    _check_category = field_validator("category")(validate_category)
    _localize = field_validator("occurred_at")(localize)


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction."""

    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    merchant: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., max_length=50)
    raw_input: str = Field(..., description="Original user input string")
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    note: Optional[str] = None
    occurred_at: Optional[datetime] = Field(
        None, description="When the purchase happened; defaults to now. Naive values are local time."
    )

    _check_category = field_validator("category")(validate_category)
    _localize = field_validator("occurred_at")(localize)


class AutoTransactionCreate(BaseModel):
    """Schema for a purchase reported by an automation (e.g. the iOS Wallet trigger)."""

    merchant: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0, description='Number or currency string like "$1,234.56"')
    card: Optional[str] = Field(None, max_length=255, description="Card or pass used")
    occurred_at: Optional[datetime] = None

    _localize = field_validator("occurred_at")(localize)

    @field_validator("amount", mode="before")
    @classmethod
    def parse_currency(cls, value: Union[str, float]) -> Union[str, float]:
        """Strip currency symbols and thousands separators from string amounts."""
        if isinstance(value, str):
            return re.sub(r"[^0-9.\-]", "", value)
        return value


class TransactionResponse(BaseModel):
    """Schema for returning a transaction in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: float
    merchant: str
    category: str
    raw_input: str
    ai_confidence: Optional[float]
    note: Optional[str]
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime
    # Set only on create: budget thresholds (80% / 100%) this purchase crossed.
    budget_alerts: list[str] = []


class BudgetUpdate(BaseModel):
    """Schema for setting a monthly budget."""

    monthly_limit: float = Field(..., gt=0, le=1_000_000)
