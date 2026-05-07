"""API routes for CRUD operations on transactions."""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import TransactionCreate, TransactionPatch, TransactionResponse
from app.models.transaction import Transaction
from app.services import merchant_learning
from app.services.charts import get_period_bounds
from app.services.db import get_session

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _coerce_amount(transaction: Transaction) -> None:
    """Ensure transaction.amount is a plain float, not a Decimal.

    asyncpg returns Decimal for Numeric columns.  Must only be called AFTER
    session.expunge(transaction) to prevent SQLAlchemy from treating the
    attribute change as a dirty write and issuing a phantom UPDATE on commit.
    """
    if isinstance(transaction.amount, Decimal):
        transaction.amount = float(transaction.amount)  # type: ignore[assignment]


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    data: TransactionCreate,
    session: AsyncSession = Depends(get_session),
) -> Transaction:
    """Create a new transaction record."""
    transaction = Transaction(**data.model_dump())
    session.add(transaction)
    await session.flush()
    await session.refresh(transaction)
    session.expunge(transaction)
    _coerce_amount(transaction)
    return transaction


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category: Optional[str] = Query(default=None),
    period: Optional[str] = Query(default=None, description="daily/weekly/monthly — filters to that period"),
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD — reference date for period filter"),
    session: AsyncSession = Depends(get_session),
) -> list[Transaction]:
    """List transactions with optional category and period filters, paginated, newest first."""
    query = select(Transaction).order_by(Transaction.created_at.desc())
    if category:
        query = query.where(Transaction.category == category)
    if period:
        start, end = get_period_bounds(period, date)
        query = query.where(Transaction.created_at >= start).where(Transaction.created_at <= end)
    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    transactions = list(result.scalars().all())
    for t in transactions:
        session.expunge(t)
        _coerce_amount(t)
    return transactions


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def patch_transaction(
    transaction_id: UUID,
    data: TransactionPatch,
    session: AsyncSession = Depends(get_session),
) -> Transaction:
    """Partially update a transaction. Records merchant-category mapping when category changes."""
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    update_data = data.model_dump(exclude_unset=True)
    if "category" in update_data:
        await merchant_learning.record_override(
            transaction.merchant, update_data["category"], session
        )
    for field, value in update_data.items():
        setattr(transaction, field, value)
    await session.flush()
    await session.refresh(transaction)
    session.expunge(transaction)
    _coerce_amount(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a transaction by ID. Returns 404 if not found."""
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await session.delete(transaction)
