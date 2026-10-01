"""Budget endpoints — monthly limits per category or overall ("Total"), with live status."""
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import BUDGET_TOTAL
from app.models.budget import Budget
from app.models.schemas import BudgetUpdate
from app.services.budgets import BUDGET_KEYS, budget_status
from app.services.db import get_session

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _check_key(category: str) -> str:
    """Reject budget keys that aren't a category or "Total"."""
    if category not in BUDGET_KEYS:
        raise HTTPException(
            status_code=422,
            detail=f"category must be one of: {', '.join(BUDGET_KEYS)}",
        )
    return category


@router.get("")
async def list_budgets(session: AsyncSession = Depends(get_session)) -> dict:
    """Return this month's status for every budget (Total first)."""
    return {"budgets": await budget_status(session)}


@router.put("/{category}")
async def set_budget(
    data: BudgetUpdate,
    category: str = Path(..., description=f"A category name or {BUDGET_TOTAL!r}"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Create or replace the monthly limit for a category (or Total) and return its status."""
    _check_key(category)
    await session.execute(
        insert(Budget)
        .values(category=category, monthly_limit=data.monthly_limit)
        .on_conflict_do_update(
            index_elements=["category"], set_={"monthly_limit": data.monthly_limit}
        )
    )
    await session.flush()
    return next(s for s in await budget_status(session) if s["category"] == category)


@router.delete("/{category}", status_code=204)
async def delete_budget(category: str, session: AsyncSession = Depends(get_session)) -> None:
    """Remove a budget. Returns 404 if none was set."""
    budget = (
        await session.execute(select(Budget).where(Budget.category == _check_key(category)))
    ).scalar_one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="No budget set for that category")
    await session.delete(budget)
