"""Monthly budget status, pace projection, and threshold alerts."""
import calendar
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import BUDGET_TOTAL, CATEGORIES, LOCAL_TZ
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.services.charts import get_period_bounds

BUDGET_KEYS = [*CATEGORIES, BUDGET_TOTAL]
WARN_AT = 0.8  # alert when a purchase pushes a budget past 80%, then again past 100%


async def _month_spent(session: AsyncSession, category: str) -> float:
    """Spend so far this local calendar month, for one category or all (Total)."""
    start, end = get_period_bounds("monthly")
    query = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.occurred_at >= start)
        .where(Transaction.occurred_at <= end)
    )
    if category != BUDGET_TOTAL:
        query = query.where(Transaction.category == category)
    return float((await session.execute(query)).scalar_one())


def _status(category: str, limit: float, spent: float, now: datetime) -> dict:
    """Derive remaining, daily allowance and month-end projection for one budget."""
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_left = days_in_month - now.day + 1  # today still counts
    projected = spent / now.day * days_in_month
    remaining = limit - spent
    return {
        "category": category,
        "monthly_limit": round(limit, 2),
        "spent": round(spent, 2),
        "remaining": round(remaining, 2),
        "percent_used": round(spent / limit * 100, 1),
        "daily_allowance": round(max(remaining, 0) / days_left, 2),
        "days_left": days_left,
        "projected": round(projected, 2),
        "on_track": projected <= limit,
    }


async def budget_status(session: AsyncSession) -> list[dict]:
    """Return this month's status for every budget, Total first, then by category order."""
    budgets = (await session.execute(select(Budget))).scalars().all()
    now = datetime.now(LOCAL_TZ)
    statuses = [
        _status(b.category, float(b.monthly_limit), await _month_spent(session, b.category), now)
        for b in budgets
    ]
    order = [BUDGET_TOTAL, *CATEGORIES]
    return sorted(statuses, key=lambda s: order.index(s["category"]))


async def alerts_for(transaction: Transaction, session: AsyncSession) -> list[str]:
    """Return alert lines if this transaction pushed its category or Total past 80% / 100%.

    Call after the transaction is flushed. Backdated purchases outside the
    current month never alert.
    """
    start, end = get_period_bounds("monthly")
    occurred = transaction.occurred_at
    if occurred.tzinfo is None:  # SQLite returns naive UTC
        occurred = occurred.replace(tzinfo=timezone.utc)
    if not (start <= occurred <= end):
        return []

    budgets = {
        b.category: float(b.monthly_limit)
        for b in (
            await session.execute(
                select(Budget).where(Budget.category.in_([transaction.category, BUDGET_TOTAL]))
            )
        ).scalars()
    }
    amount = float(transaction.amount)
    now = datetime.now(LOCAL_TZ)
    alerts = []
    for category, limit in budgets.items():
        after = await _month_spent(session, category)
        before = after - amount
        label = "your total budget" if category == BUDGET_TOTAL else f"your {category} budget"
        if before <= limit < after:
            alerts.append(f"🚨 Over {label}: ${after:,.2f} of ${limit:,.2f} this month.")
        elif before < limit * WARN_AT <= after:
            s = _status(category, limit, after, now)
            alerts.append(
                f"⚠️ {s['percent_used']:.0f}% of {label} used: ${s['remaining']:,.2f} left "
                f"for {s['days_left']} days (${s['daily_allowance']:,.2f}/day)."
            )
    return alerts
