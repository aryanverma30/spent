"""Tests for budgets: endpoints, status math, threshold alerts, and summary comparison."""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import LOCAL_TZ
from app.models.transaction import Transaction
from app.routes.summary import _previous_bounds
from app.services import assistant
from app.services.budgets import _status
from app.services.charts import get_period_bounds

pytestmark = pytest.mark.asyncio

FOOD = "/api/v1/budgets/Food%20%26%20Drink"
TOTAL = "/api/v1/budgets/Total"


async def _spend(client: AsyncClient, amount: float, category: str = "Food & Drink", **extra) -> dict:
    """Log a transaction through the API and return the response body."""
    resp = await client.post("/api/v1/transactions", json={
        "amount": amount, "merchant": "Test", "category": category, "raw_input": "test", **extra,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Endpoints ────────────────────────────────────────────────────────────────


async def test_set_list_and_delete_budget(client: AsyncClient) -> None:
    """PUT creates/updates a budget, GET lists Total first, DELETE removes it."""
    resp = await client.put(FOOD, json={"monthly_limit": 300})
    assert resp.status_code == 200
    assert resp.json()["monthly_limit"] == 300.0 and resp.json()["spent"] == 0.0

    await client.put(FOOD, json={"monthly_limit": 250})  # update in place
    await client.put(TOTAL, json={"monthly_limit": 2000})
    budgets = (await client.get("/api/v1/budgets")).json()["budgets"]
    assert [(b["category"], b["monthly_limit"]) for b in budgets] == [("Total", 2000.0), ("Food & Drink", 250.0)]

    assert (await client.delete(FOOD)).status_code == 204
    assert (await client.delete(FOOD)).status_code == 404


async def test_budget_rejects_unknown_category_and_bad_amounts(client: AsyncClient) -> None:
    """Only real categories or Total, and only positive limits."""
    assert (await client.put("/api/v1/budgets/Dining", json={"monthly_limit": 100})).status_code == 422
    assert (await client.put(FOOD, json={"monthly_limit": 0})).status_code == 422


async def test_status_reflects_spending(client: AsyncClient) -> None:
    """Spent / remaining / percent track this month's transactions in that category only."""
    await _spend(client, 40)
    await _spend(client, 500, category="Travel")
    status = (await client.put(FOOD, json={"monthly_limit": 200})).json()
    assert status["spent"] == 40.0
    assert status["remaining"] == 160.0
    assert status["percent_used"] == 20.0


def test_status_math_mid_month() -> None:
    """On Sept 10 with $150 of $300 spent: 21 days left, $7.14/day, projected $450 (off track)."""
    s = _status("Food & Drink", 300.0, 150.0, datetime(2026, 9, 10, 12, tzinfo=LOCAL_TZ))
    assert s["days_left"] == 21
    assert s["daily_allowance"] == 7.14
    assert s["projected"] == 450.0
    assert s["on_track"] is False


# ── Alerts ───────────────────────────────────────────────────────────────────


async def test_alerts_fire_once_at_80_and_once_at_100(client: AsyncClient) -> None:
    """A purchase that crosses 80% warns; one that crosses 100% says over; others stay quiet."""
    await client.put(FOOD, json={"monthly_limit": 100})

    assert (await _spend(client, 50))["budget_alerts"] == []        # 50%
    warn = (await _spend(client, 35))["budget_alerts"]              # 85%
    assert len(warn) == 1 and warn[0].startswith("⚠️ 85% of your Food & Drink budget used: $15.00 left")
    over = (await _spend(client, 20))["budget_alerts"]              # 105%
    assert over == ["🚨 Over your Food & Drink budget: $105.00 of $100.00 this month."]
    assert (await _spend(client, 5))["budget_alerts"] == []         # already over


async def test_total_budget_alerts_across_categories(client: AsyncClient) -> None:
    """The Total budget counts every category."""
    await client.put(TOTAL, json={"monthly_limit": 100})
    await _spend(client, 70, category="Transport")
    alerts = (await _spend(client, 15, category="Shopping"))["budget_alerts"]
    assert len(alerts) == 1 and "your total budget" in alerts[0]


async def test_backdated_purchase_from_last_month_does_not_alert(client: AsyncClient) -> None:
    """Only purchases in the current month can trip this month's budget."""
    await client.put(FOOD, json={"monthly_limit": 10})
    last_month = (datetime.now(LOCAL_TZ).replace(day=1) - timedelta(days=5)).date().isoformat()
    assert (await _spend(client, 50, occurred_at=last_month))["budget_alerts"] == []


# ── Summary comparison & assistant tool ──────────────────────────────────────


async def test_summary_compares_with_same_point_last_period(client: AsyncClient, session: AsyncSession) -> None:
    """previous_total counts only spending up to the same elapsed point in the previous month."""
    start, end = get_period_bounds("monthly")
    prev_start, prev_end = _previous_bounds("monthly", start, end)
    for amount, when in [("40.00", prev_start + (prev_end - prev_start) / 2),  # inside window
                         ("999.00", prev_end + timedelta(minutes=1))]:      # after the cut-off
        session.add(Transaction(merchant="Old", category="Other", amount=Decimal(amount),
                                raw_input="old", occurred_at=when.astimezone(timezone.utc)))
    await session.commit()
    await _spend(client, 50)

    body = (await client.get("/api/v1/summary", params={"period": "monthly"})).json()
    assert body["total_spent"] == 50.0
    assert body["previous_total"] == 40.0
    assert body["change_pct"] == 25.0


async def test_summary_change_pct_is_null_without_history(client: AsyncClient) -> None:
    """No previous spending means no percentage (rather than divide-by-zero)."""
    await _spend(client, 10)
    body = (await client.get("/api/v1/summary")).json()
    assert body["previous_total"] == 0.0 and body["change_pct"] is None


async def test_assistant_budget_tool(client: AsyncClient, session: AsyncSession) -> None:
    """The assistant's budget_status tool returns the same data as GET /budgets."""
    await client.put(FOOD, json={"monthly_limit": 300})
    outcome = await assistant._run_tool("budget_status", {}, session)
    assert json.loads(outcome["content"])["budgets"][0]["category"] == "Food & Drink"
