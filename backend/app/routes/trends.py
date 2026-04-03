"""Trends endpoint — spending bucketed over time for daily/weekly/monthly views."""
from typing import Literal
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.services.db import get_session

router = APIRouter(prefix="/trends", tags=["trends"])


async def get_trend_buckets(period: str, session: AsyncSession) -> list[dict]:
    """Compute spending buckets for the given period type."""
    now = datetime.now(timezone.utc)

    if period == "daily":
        start = now - timedelta(days=14)
        trunc = "day"
        fmt = "%b %d"
    elif period == "weekly":
        start = now - timedelta(weeks=12)
        trunc = "week"
        fmt = "%b %d"
    else:  # monthly
        start = now - timedelta(days=180)
        trunc = "month"
        fmt = "%b %Y"

    result = await session.execute(
        select(
            func.date_trunc(trunc, Transaction.created_at).label("bucket"),
            func.sum(Transaction.amount).label("total"),
        )
        .where(Transaction.created_at >= start)
        .group_by("bucket")
        .order_by("bucket")
    )
    rows = result.all()

    return [
        {"label": row.bucket.strftime(fmt), "total": float(row.total)}
        for row in rows
    ]


@router.get("")
async def get_trends(
    period: Literal["monthly", "weekly", "daily"] = Query(default="monthly"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return spending buckets over time for charting."""
    buckets = await get_trend_buckets(period, session)

    return {
        "period": period,
        "buckets": buckets,
        "chart_url": f"/api/v1/charts/trend?period=period",
    }
