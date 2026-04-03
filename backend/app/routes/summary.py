"""Summary endpoint — spending breakdown by category for a given period."""
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.services.charts import get_period_bounds, CATEGORY_COLORS
from app.services.db import get_session

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("")
async def get_summary(
    period: Literal["monthly", "weekly", "daily"] = Query(default="monthly"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return spending totals grouped by category for the given period."""
    start, end = get_period_bounds(period)

    result = await session.execute(
        select(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.created_at >= start)
        .where(Transaction.created_at < end)
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    )
    rows = result.all()

    breakdown = [
        {
            "category": row.category,
            "total": float(row.total),
            "count": row.count,
            "color": CATEGORY_COLORS.get(row.category, "#B0BEC5"),
        }
        for row in rows
    ]

    total_spent = sum(item["total"] for item in breakdown)

    return {
        "period": period,
        "total_spent": total_spent,
        "breakdown": breakdown,
        "chart_url": f"/api/v1/charts/donut?period={period}",
    }
