"""Pydantic v2 schemas for request validation and response serialization."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import CATEGORIES


def validate_category(value: str | None) -> str | None:
    """Reject category names that aren't in the shared CATEGORIES list."""
    if value is not None and value not in CATEGORIES:
        raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
    return value


class TransactionPatch(BaseModel):
    """Schema for partially updating a transaction (PATCH)."""

    category: Optional[str] = Field(None, max_length=50)
    note: Optional[str] = None

    _check_category = field_validator("category")(validate_category)


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction."""

    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    merchant: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., max_length=50)
    raw_input: str = Field(..., description="Original user input string")
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    note: Optional[str] = None

    _check_category = field_validator("category")(validate_category)


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
    created_at: datetime
    updated_at: datetime
