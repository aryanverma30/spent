"""AI insights endpoint — generates a spending summary for the current calendar month."""
import calendar
import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CATEGORY_COLORS, LOCAL_TZ
from app.models.transaction import Transaction
from app.services.ai import generate_insights
from app.services.charts import get_period_bounds
from app.services.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("")
async def get_insights(session: AsyncSession = Depends(get_session)) -> dict:
    """Get AI-generated spending insights for the current calendar month."""
    try:
        # Same local-time month boundaries as /summary, so the two always agree.
        now = datetime.now(LOCAL_TZ)
        start, end = get_period_bounds("monthly")

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

        if not breakdown:
            return {"summary": "No spending recorded yet this month. Start logging expenses to see AI insights!"}

        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_remaining = days_in_month - now.day

        summary = await generate_insights(breakdown, days_remaining)
        return {"summary": summary}
    except Exception:
        logger.exception("Unexpected error in get_insights")
        return {"summary": "Insights temporarily unavailable. Try again later."}
