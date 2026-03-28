"""
Transactions routes — Phase 1.

Endpoints:
  POST /api/v1/transactions   — create a new transaction
  GET  /api/v1/transactions   — list transactions (paginated, filterable by category)

Both endpoints use an async SQLAlchemy session injected via FastAPI's Depends().
The session is provided by get_session() in services/db.py.

SQLAlchemy query pattern used here:
  result = await session.execute(select(Transaction).where(...).order_by(...))
  rows = result.scalars().all()   # .scalars() unwraps the Row wrapper
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import TransactionCreate, TransactionResponse
from app.models.transaction import Transaction
from app.services.db import get_session

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionResponse,
    summary="Create a new transaction",
)
async def create_transaction(
    data: TransactionCreate,
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    """
    Create and persist a new transaction.

    The request body is validated by TransactionCreate (Pydantic).
    The created transaction is returned as a TransactionResponse.

    TODO: Implement this endpoint.
    Steps to complete:
        1. Create a Transaction ORM instance from `data`:
               transaction = Transaction(**data.model_dump())
           `model_dump()` converts the Pydantic model to a plain dict.

        2. Add it to the session and flush to get the DB-generated id:
               session.add(transaction)
               await session.flush()   # sends INSERT but doesn't commit yet

        3. Refresh to load server-generated fields (created_at, updated_at):
               await session.refresh(transaction)

        4. Return the ORM instance — FastAPI will convert it via TransactionResponse.
           (The session commits automatically in get_session() after yield.)

    Hint — the full implementation is ~5 lines:
        transaction = Transaction(**data.model_dump())
        session.add(transaction)
        await session.flush()
        await session.refresh(transaction)
        return transaction
    """
    # TODO: Replace this with the real implementation described above.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="create_transaction() is not yet implemented — see the TODO above.",
    )


@router.get(
    "/",
    response_model=list[TransactionResponse],
    summary="List transactions",
)
async def list_transactions(
    limit: int = 10,
    offset: int = 0,
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
) -> list[TransactionResponse]:
    """
    Return a paginated list of transactions, newest first.

    Query parameters:
      limit    — max number of results (default 10)
      offset   — skip this many results for pagination (default 0)
      category — if provided, filter to only this category (e.g. "food")

    TODO: Implement this endpoint.
    Steps to complete:
        1. Start building a SELECT query:
               query = select(Transaction).order_by(Transaction.created_at.desc())

        2. If `category` was provided, add a WHERE filter:
               if category:
                   query = query.where(Transaction.category == category)

        3. Apply pagination using .limit() and .offset():
               query = query.limit(limit).offset(offset)

        4. Execute the query and unpack the rows:
               result = await session.execute(query)
               transactions = result.scalars().all()

        5. Return the list — FastAPI converts each item via TransactionResponse.

    Hint — the full implementation is ~7 lines.
    """
    # TODO: Replace this with the real implementation described above.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="list_transactions() is not yet implemented — see the TODO above.",
    )
