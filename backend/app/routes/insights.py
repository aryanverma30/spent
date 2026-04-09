"""AI insights endpoint — generates a spending summary for the current month."""
import calendar
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.services.ai import generate_insights
from app.services.db import get_session

router = APIRouter(prefix="/insights", tags=["insights"])

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
async def get_insights(session: AsyncSession = Depends(get_session)) -> dict:
    """Get AI-generated spending insights for the current calendar month."""
    try:
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await session.execute(
            select(
                Transaction.category,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .where(Transaction.created_at >= start_of_month)
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
    except Exception as e:
        return {"summary": f"Insights temporarily unavailable. Try again later."}
