"""API routes for CRUD operations on transactions."""
import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.schemas import (
    AutoTransactionCreate,
    TransactionCreate,
    TransactionPatch,
    TransactionResponse,
)
from app.models.transaction import Transaction
from app.services import merchant_learning
from app.services.ai import parse_transaction
from app.services.budgets import alerts_for
from app.services.charts import get_period_bounds
from app.services.db import get_session
from app.services.telegram import notify_auto_logged

logger = logging.getLogger(__name__)

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
) -> TransactionResponse:
    """Create a new transaction record, reporting any budget thresholds it crossed."""
    # exclude_none so an omitted occurred_at falls back to the server default (now).
    transaction = Transaction(**data.model_dump(exclude_none=True))
    session.add(transaction)
    await session.flush()
    await session.refresh(transaction)
    alerts = await alerts_for(transaction, session)
    session.expunge(transaction)
    _coerce_amount(transaction)
    return TransactionResponse.model_validate(transaction).model_copy(update={"budget_alerts": alerts})


async def _categorize(merchant: str, amount: float, session: AsyncSession) -> tuple[str, float]:
    """Return (category, confidence): a learned merchant rule first, then Claude.

    Never raises — if the AI is unavailable the purchase is still logged as
    Other with zero confidence so it gets flagged for review.
    """
    override = await merchant_learning.get_override(merchant, session)
    if override:
        return override, 1.0
    try:
        result = await parse_transaction(f"${amount:.2f} {merchant}")
    except Exception:
        logger.exception("AI categorization failed for auto-logged %r", merchant)
        return "Other", 0.0
    if "category" not in result:
        return "Other", 0.0
    confidence = min(max(float(result.get("confidence", 0.0)), 0.0), 1.0)
    return result["category"], confidence


@router.post("/auto", response_model=TransactionResponse, status_code=201)
async def auto_log_transaction(
    data: AutoTransactionCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> TransactionResponse:
    """Log a purchase reported by an automation (iOS Wallet trigger) and notify via Telegram."""
    category, confidence = await _categorize(data.merchant, data.amount, session)

    raw_input = f"[auto] {data.merchant} ${data.amount:.2f}"
    if data.card:
        raw_input += f" via {data.card}"

    transaction = Transaction(
        amount=data.amount,
        merchant=data.merchant,
        category=category,
        raw_input=raw_input,
        ai_confidence=confidence,
    )
    if data.occurred_at:
        transaction.occurred_at = data.occurred_at
    session.add(transaction)
    await session.flush()
    await session.refresh(transaction)
    alerts = await alerts_for(transaction, session)
    session.expunge(transaction)
    _coerce_amount(transaction)

    # Runs after the response is sent and the session has committed.
    background_tasks.add_task(
        notify_auto_logged, transaction, confidence < settings.ai_confidence_threshold, alerts
    )
    return TransactionResponse.model_validate(transaction).model_copy(update={"budget_alerts": alerts})


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
    query = select(Transaction).order_by(Transaction.occurred_at.desc())
    if category:
        query = query.where(Transaction.category == category)
    if period:
        start, end = get_period_bounds(period, date)
        query = query.where(Transaction.occurred_at >= start).where(Transaction.occurred_at <= end)
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
