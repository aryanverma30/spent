"""Categories endpoint — return the supported category list with period spending totals."""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CATEGORIES, CATEGORY_COLORS
from app.models.transaction import Transaction
from app.services.charts import get_period_bounds
from app.services.db import get_session

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(
    period: Literal["monthly", "weekly", "daily"] = Query(default="monthly"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return all supported categories with their spending totals for the given period.

    Categories with no spending in the period are included with total=0 so the
    widget can always render a complete list without a separate static lookup.
    """
    start, end = get_period_bounds(period)

    result = await session.execute(
        select(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.occurred_at >= start)
        .where(Transaction.occurred_at <= end)
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
