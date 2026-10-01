"""Summary endpoint — spending breakdown by category for a given period."""
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CATEGORY_COLORS, LOCAL_TZ
from app.models.transaction import Transaction
from app.services.charts import get_period_bounds
from app.services.db import get_session

router = APIRouter(prefix="/summary", tags=["summary"])


def _previous_bounds(period: str, start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """The previous period, cut off at the same elapsed point (e.g. Aug 1–15 vs Sep 1–15)."""
    day_before = (start.astimezone(LOCAL_TZ) - timedelta(days=1)).date().isoformat()
    prev_start, prev_natural_end = get_period_bounds(period, day_before)
    return prev_start, min(prev_start + (end - start), prev_natural_end)


@router.get("")
async def get_summary(
    period: Literal["monthly", "weekly", "daily"] = Query(default="monthly"),
    date: str | None = Query(default=None, description="YYYY-MM-DD reference date; defaults to today"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return spending totals grouped by category for the given period and optional date."""
    start, end = get_period_bounds(period, date)

    result = await session.execute(
        select(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.occurred_at >= start)
        .where(Transaction.occurred_at <= end)
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

    total_spent = float(sum(item["total"] for item in breakdown))

    prev_start, prev_end = _previous_bounds(period, start, end)
    previous_total = float(
        (
            await session.execute(
                select(func.coalesce(func.sum(Transaction.amount), 0))
                .where(Transaction.occurred_at >= prev_start)
                .where(Transaction.occurred_at <= prev_end)
            )
        ).scalar_one()
    )

    return {
        "period": period,
        "total_spent": total_spent,
        # Same elapsed point in the previous period, so mid-month compares like with like.
        "previous_total": round(previous_total, 2),
        "change_pct": (
            round((total_spent - previous_total) / previous_total * 100, 1) if previous_total else None
        ),
        "breakdown": breakdown,
        "chart_url": f"/api/v1/charts/donut?period={period}",
    }
