"""Categories endpoint — return the supported category list with period spending totals."""
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.services.db import get_session

router = APIRouter(prefix="/categories", tags=["categories"])

CATEGORIES: list[str] = [
    "Food & Drink",
    "Transport",
    "Entertainment",
    "Shopping",
    "Health",
    "Utilities",
    "Travel",
    "Other",
]

CATEGORY_COLORS: dict[str, str] = {
    "Food & Drink": "#FF6B6B",
    "Transport": "#4ECDC4",
    "Entertainment": "#45B7D1",
    "Shopping": "#96CEB4",
    "Health": "#FFEAA7",
    "Utilities": "#DDA0DD",
    "Travel": "#F0A500",
    "Other": "#B0BEC5",
}


@router.get("")
async def list_categories(
    period: Literal["monthly", "weekly", "daily"] = Query(default="monthly"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return all supported categories with their spending totals for the given period.

    Categories with no spending in the period are included with total=0 so the
    widget can always render a complete list without a separate static lookup.
    """
    from app.services.charts import get_period_bounds

    start, end = get_period_bounds(period)

    result = await session.execute(
        select(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.created_at >= start)
        .where(Transaction.created_at <= end)
        .group_by(Transaction.category)
    )
    rows = {row.category: {"total": float(row.total), "count": row.count} for row in result.all()}

    categories = [
        {
            "name": cat,
            "color": CATEGORY_COLORS.get(cat, "#B0BEC5"),
            "total": rows.get(cat, {}).get("total", 0.0),
            "count": rows.get(cat, {}).get("count", 0),
        }
        for cat in CATEGORIES
    ]

    return {"period": period, "categories": categories}
