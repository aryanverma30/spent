"""AI endpoints for parsing natural language transaction input."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ai import parse_transaction

router = APIRouter(prefix="/ai", tags=["ai"])


class ParseRequest(BaseModel):
    """Request body for the AI parse endpoint."""

    raw_input: str


@router.post("/parse")
async def parse_transaction_endpoint(request: ParseRequest) -> dict:
    """Parse a natural language string into structured transaction data.

    Returns parsed fields or {"error": "not_a_transaction"} if the input
    is not a valid spending entry.
    """
    try:
        result = await parse_transaction(request.raw_input)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI parsing failed: {e!s}")
