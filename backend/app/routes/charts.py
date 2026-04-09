"""Chart image endpoints — return Matplotlib-rendered PNG images."""
from typing import Literal
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.services.charts import (
    generate_donut_chart,
    get_period_bounds,
)
from app.services.db import get_session

router = APIRouter(prefix="/charts", tags=["charts"])


@router.get("/donut")
async def donut_chart(
    period: Literal["monthly", "weekly", "daily"] = Query(default="monthly"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Return a PNG donut chart of spending by category for the given period."""
    start, end = get_period_bounds(period)

    result = await session.execute(
        select(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
        )
        .where(Transaction.created_at >= start)
        .where(Transaction.created_at <= end)
        .group_by(Transaction.category)
    )
    rows = result.all()

    breakdown = [
        {"category": row.category, "total": float(row.total)}
        for row in rows
    ]

    png_bytes = generate_donut_chart(breakdown)
    return Response(content=png_bytes, media_type="image/png")
