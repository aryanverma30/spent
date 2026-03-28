"""
Pydantic v2 request and response schemas.

Schemas are the "shape" of data going in and out of the API — they are
separate from SQLAlchemy models (which describe the database).

Two schemas are needed for transactions:

  TransactionCreate  — what the client SENDS in a POST request body
  TransactionResponse — what the API RETURNS in every response

Why keep them separate?
  - TransactionCreate has no id, created_at, or updated_at (the DB generates these)
  - TransactionResponse includes all fields including the DB-generated ones
  - This prevents clients from accidentally overwriting server-managed fields

Pydantic v2 changes from v1:
  - `orm_mode = True`  →  `model_config = ConfigDict(from_attributes=True)`
  - `.dict()`          →  `.model_dump()`
  - `.parse_obj()`     →  `.model_validate()`
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    """
    Schema for creating a new transaction (POST /transactions request body).

    All fields here map directly to columns in the transactions table,
    except for the server-generated ones (id, created_at, updated_at).

    Example JSON:
        {
            "amount": 12.00,
            "merchant": "Chipotle",
            "category": "food",
            "raw_input": "12 chipotle bowl",
            "ai_confidence": 0.95,
            "note": "lunch with friends"
        }
    """

    # TODO: Define the `amount` field.
    # Hint: use float as the type, and Field(gt=0) to ensure it's positive.
    #   amount: float = Field(..., gt=0, description="Transaction amount in USD")

    # TODO: Define `merchant` — a non-empty string.
    # Hint: Field(..., min_length=1, max_length=255)

    # TODO: Define `category` — a non-empty string, max 50 chars.

    # TODO: Define `raw_input` — the original user input text.

    # TODO: Define `ai_confidence` — optional float between 0 and 1.
    # Hint: Optional[float] = Field(None, ge=0.0, le=1.0)

    # TODO: Define `note` — optional text.
    # Hint: Optional[str] = None


class TransactionResponse(BaseModel):
    """
    Schema for returning a transaction in API responses.

    `from_attributes=True` tells Pydantic to read values from ORM object
    attributes (e.g. transaction.id) instead of dict keys. This is required
    to convert SQLAlchemy model instances to Pydantic models.

    Usage in a route:
        transaction = await session.get(Transaction, some_id)
        return TransactionResponse.model_validate(transaction)
    """

    # This config is already provided — do not remove it.
    model_config = ConfigDict(from_attributes=True)

    # TODO: Define all fields that should be included in the API response.
    # These must match the column names on the Transaction ORM model.
    #
    # Fields to include:
    #   id            — uuid.UUID
    #   amount        — float
    #   merchant      — str
    #   category      — str
    #   raw_input     — str
    #   ai_confidence — Optional[float]
    #   note          — Optional[str]
    #   created_at    — datetime
    #   updated_at    — datetime
    #
    # Hint: copy the field names from TransactionCreate and add the server fields.
