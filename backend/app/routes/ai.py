"""AI endpoints for parsing natural language transaction input and recording learned mappings."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai import parse_transaction
from app.services.db import get_session
from app.services import merchant_learning

router = APIRouter(prefix="/ai", tags=["ai"])


class ParseRequest(BaseModel):
    """Request body for the AI parse endpoint."""

    raw_input: str


class LearnRequest(BaseModel):
    """Request body for recording a user-confirmed merchant-category mapping."""

    merchant: str
    category: str


@router.post("/parse")
async def parse_transaction_endpoint(
    request: ParseRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Parse a natural language string into structured transaction data.

    Returns parsed fields, a spending_query descriptor, or {"error": "not_a_transaction"}.
    For expense results, applies any user-learned merchant overrides before returning.
    """
    try:
        result = await parse_transaction(request.raw_input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI parsing failed: {e!s}")

    # Apply learned merchant override if this is an expense (not a query or error)
    if "amount" in result and "merchant" in result:
        override = await merchant_learning.get_override(result["merchant"], session)
        if override:
            result["category"] = override
            result["confidence"] = 1.0

    return result


@router.post("/learn")
async def learn_merchant_category(
    request: LearnRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Record a user-confirmed merchant-to-category mapping for future auto-categorization."""
    await merchant_learning.record_override(request.merchant, request.category, session)
    return {"status": "ok"}
