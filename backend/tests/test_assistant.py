"""Tests for services/assistant.py (query tools + tool-use loop) and POST /ai/ask."""
import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.services import assistant

pytestmark = pytest.mark.asyncio


def _utc(month: int, day: int, hour: int = 18) -> datetime:
    """A 2026 UTC timestamp (18:00 UTC is early afternoon in Chicago)."""
    return datetime(2026, month, day, hour, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def seeded(session: AsyncSession) -> None:
    """Seed a small ledger across August and September 2026."""
    rows = [
        ("Chipotle", "Food & Drink", "12.50", _utc(9, 2)),
        ("Whole Foods", "Groceries", "84.20", _utc(9, 3)),
        ("STARBUCKS #123", "Food & Drink", "6.45", _utc(9, 5)),
        ("Delta", "Travel", "320.00", _utc(9, 10)),
        ("Starbucks", "Food & Drink", "5.95", _utc(9, 12)),
        ("Uber", "Transport", "22.00", _utc(9, 14)),
        ("Chipotle", "Food & Drink", "11.00", _utc(8, 20)),
        # 22:00 Aug 31 in Chicago, already Sept 1 in UTC — must count as August.
        ("Late Night Tacos", "Food & Drink", "9.00", _utc(9, 1, hour=3)),
    ]
    for merchant, category, amount, when in rows:
        session.add(Transaction(
            merchant=merchant, category=category, amount=Decimal(amount),
            raw_input=f"{merchant} {amount}", occurred_at=when,
        ))
    await session.commit()


SEPT = {"start_date": "2026-09-01", "end_date": "2026-09-30"}
AUG = {"start_date": "2026-08-01", "end_date": "2026-08-31"}


# ── Tools ────────────────────────────────────────────────────────────────────


async def test_top_purchases_by_amount(seeded: None, session: AsyncSession) -> None:
    """sort_by=amount + limit returns the biggest purchases and the full match count."""
    result = await assistant.find_transactions(
        {**SEPT, "sort_by": "amount", "descending": True, "limit": 3}, session
    )
    assert result["matched"] == 6
    assert [t["merchant"] for t in result["transactions"]] == ["Delta", "Whole Foods", "Uber"]
    assert result["transactions"][0] == {
        "date": "2026-09-10", "merchant": "Delta", "category": "Travel", "amount": 320.0,
    }


async def test_merchant_filter_is_case_insensitive_substring(seeded: None, session: AsyncSession) -> None:
    """merchant_contains matches 'STARBUCKS #123' and 'Starbucks' alike."""
    result = await assistant.find_transactions({**SEPT, "merchant_contains": "starbucks"}, session)
    assert result["matched"] == 2


async def test_dates_are_bucketed_in_local_time(seeded: None, session: AsyncSession) -> None:
    """A purchase late on Aug 31 local time belongs to August even though it's Sept 1 in UTC."""
    aug = await assistant.find_transactions(AUG, session)
    assert {t["merchant"] for t in aug["transactions"]} == {"Chipotle", "Late Night Tacos"}
    assert next(t for t in aug["transactions"] if t["merchant"] == "Late Night Tacos")["date"] == "2026-08-31"


async def test_totals_by_category_sorted_by_total(seeded: None, session: AsyncSession) -> None:
    """group_by=category sums per category, highest first, with share of total."""
    result = await assistant.spending_totals({**SEPT, "group_by": "category"}, session)
    assert result["total"] == 451.10
    assert result["count"] == 6
    first = result["groups"][0]
    assert first["group"] == "Travel" and first["total"] == 320.0 and first["share_of_total"] == "71%"
    food = next(g for g in result["groups"] if g["group"] == "Food & Drink")
    assert food == {"group": "Food & Drink", "total": 24.9, "count": 3, "average": 8.3, "share_of_total": "6%"}


async def test_totals_by_month_are_chronological(seeded: None, session: AsyncSession) -> None:
    """group_by=month returns months in order, with category filtering applied."""
    result = await assistant.spending_totals(
        {"start_date": "2026-08-01", "end_date": "2026-09-30", "group_by": "month", "category": "Food & Drink"},
        session,
    )
    assert [(g["group"], g["total"]) for g in result["groups"]] == [("2026-08", 20.0), ("2026-09", 24.9)]


async def test_bad_dates_become_tool_errors(session: AsyncSession) -> None:
    """Invalid input is reported back to Claude as an is_error tool result, not raised."""
    outcome = await assistant._run_tool(
        "spending_totals", {"start_date": "2026-09-30", "end_date": "2026-09-01", "group_by": "none"}, session
    )
    assert outcome["is_error"] is True
    assert "before start_date" in outcome["content"]


# ── Tool-use loop ────────────────────────────────────────────────────────────


def _response(stop_reason: str, *blocks: SimpleNamespace) -> SimpleNamespace:
    """Build a minimal stand-in for an Anthropic Message."""
    return SimpleNamespace(stop_reason=stop_reason, content=list(blocks))


def _text(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_use(name: str, tool_input: dict, block_id: str = "toolu_1") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=tool_input)


def _mock_client(*responses: SimpleNamespace) -> AsyncMock:
    client = AsyncMock()
    client.beta.messages.create = AsyncMock(side_effect=list(responses))
    return client


async def test_loop_runs_tool_and_returns_final_text(seeded: None, session: AsyncSession) -> None:
    """Claude calls a tool, gets the real result back, then answers."""
    call = _tool_use("find_transactions", {**SEPT, "sort_by": "amount", "limit": 1})
    client = _mock_client(
        _response("tool_use", call),
        _response("end_turn", _text("Your biggest purchase was Delta at $320.00.")),
    )
    with patch("app.services.assistant.get_client", return_value=client):
        answer = await assistant.answer_question("biggest purchase this month?", session)

    assert answer == "Your biggest purchase was Delta at $320.00."
    second_call_messages = client.beta.messages.create.await_args_list[1].kwargs["messages"]
    assert second_call_messages[1] == {"role": "assistant", "content": [call]}
    result_block = second_call_messages[2]["content"][0]
    assert result_block["tool_use_id"] == "toolu_1"
    assert json.loads(result_block["content"])["transactions"][0]["merchant"] == "Delta"


async def test_loop_uses_fallbacks_and_no_forced_tool_choice(session: AsyncSession) -> None:
    """Requests opt into server-side fallbacks and leave tool_choice at auto."""
    client = _mock_client(_response("end_turn", _text("ok")))
    with patch("app.services.assistant.get_client", return_value=client):
        await assistant.answer_question("hi", session)
    kwargs = client.beta.messages.create.await_args.kwargs
    assert kwargs["model"] == "claude-opus-5-5"
    assert kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]
    assert "tool_choice" not in kwargs


async def test_loop_handles_refusal(session: AsyncSession) -> None:
    """A refusal stop reason returns a friendly message instead of empty text."""
    client = _mock_client(_response("refusal"))
    with patch("app.services.assistant.get_client", return_value=client):
        assert "can't help" in await assistant.answer_question("?", session)


async def test_loop_stops_after_max_rounds(seeded: None, session: AsyncSession) -> None:
    """A model that never stops calling tools is cut off after MAX_TOOL_ROUNDS."""
    call = _tool_use("spending_totals", {**SEPT, "group_by": "none"})
    client = _mock_client(*[_response("tool_use", call)] * assistant.MAX_TOOL_ROUNDS)
    with patch("app.services.assistant.get_client", return_value=client):
        answer = await assistant.answer_question("loop forever", session)
    assert "breaking it up" in answer
    assert client.beta.messages.create.await_count == assistant.MAX_TOOL_ROUNDS


# ── Endpoint ─────────────────────────────────────────────────────────────────


async def test_ask_endpoint_returns_answer(client: AsyncClient) -> None:
    """POST /ai/ask returns the assistant's answer."""
    with patch("app.routes.ai.answer_question", AsyncMock(return_value="$451.10 so far.")):
        resp = await client.post("/api/v1/ai/ask", json={"question": "how much this month?"})
    assert resp.status_code == 200
    assert resp.json() == {"answer": "$451.10 so far."}


async def test_ask_endpoint_503_when_ai_unavailable(client: AsyncClient) -> None:
    """AI failures surface as 503 so the bot can show a retry message."""
    with patch("app.routes.ai.answer_question", AsyncMock(side_effect=RuntimeError("no key"))):
        resp = await client.post("/api/v1/ai/ask", json={"question": "?"})
    assert resp.status_code == 503
