"""Tests for POST /api/v1/transactions/auto, occurred_at, and the Telegram notifier."""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.config import settings
from app.models.transaction import Transaction
from app.services.telegram import notify_auto_logged

pytestmark = pytest.mark.asyncio

_AUTO = {"merchant": "Starbucks", "amount": "$6.45", "card": "Apple Card"}


@pytest.fixture
def notify():
    """Replace the Telegram notification with a mock and return it."""
    with patch("app.routes.transactions.notify_auto_logged", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def ai():
    """Replace Claude categorization with a mock and return it."""
    with patch("app.routes.transactions.parse_transaction", new_callable=AsyncMock) as mock:
        yield mock


async def test_auto_log_uses_ai_category(client: AsyncClient, notify: AsyncMock, ai: AsyncMock) -> None:
    """The AI category and confidence are saved and a high-confidence notification is sent."""
    ai.return_value = {"amount": 6.45, "merchant": "Starbucks", "category": "Food & Drink", "confidence": 0.95}

    resp = await client.post("/api/v1/transactions/auto", json=_AUTO)

    assert resp.status_code == 201
    body = resp.json()
    assert body["category"] == "Food & Drink"
    assert body["amount"] == 6.45
    assert body["raw_input"] == "[auto] Starbucks $6.45 via Apple Card"
    notify.assert_awaited_once()
    assert notify.await_args.args[1] is False  # needs_review


async def test_auto_log_prefers_learned_merchant_rule(
    client: AsyncClient, notify: AsyncMock, ai: AsyncMock
) -> None:
    """A learned merchant→category rule wins and Claude isn't called."""
    await client.post("/api/v1/ai/learn", json={"merchant": "Starbucks", "category": "Groceries"})

    resp = await client.post("/api/v1/transactions/auto", json=_AUTO)

    assert resp.json()["category"] == "Groceries"
    assert resp.json()["ai_confidence"] == 1.0
    ai.assert_not_awaited()


async def test_auto_log_still_saves_when_ai_fails(
    client: AsyncClient, notify: AsyncMock, ai: AsyncMock
) -> None:
    """If Claude is down the purchase is saved as Other and flagged for review."""
    ai.side_effect = RuntimeError("AI service unavailable")

    resp = await client.post("/api/v1/transactions/auto", json=_AUTO)

    assert resp.status_code == 201
    assert resp.json()["category"] == "Other"
    assert notify.await_args.args[1] is True  # needs_review


async def test_auto_log_rejects_non_positive_amount(client: AsyncClient, notify: AsyncMock) -> None:
    """Refunds / zero amounts are rejected rather than logged as spending."""
    resp = await client.post("/api/v1/transactions/auto", json={**_AUTO, "amount": "-$6.45"})
    assert resp.status_code == 422
    notify.assert_not_awaited()


async def test_create_accepts_backdated_occurred_at(client: AsyncClient) -> None:
    """A bare date is stored as that local day; created_at still reflects logging time."""
    resp = await client.post(
        "/api/v1/transactions",
        json={
            "amount": 12.0,
            "merchant": "Chipotle",
            "category": "Food & Drink",
            "raw_input": "$12 Chipotle on Sept 1",
            "occurred_at": "2026-09-01",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["occurred_at"].startswith("2026-09-01")
    assert body["created_at"] != body["occurred_at"]


async def test_create_defaults_occurred_at_to_now(client: AsyncClient) -> None:
    """Omitting occurred_at falls back to the server default instead of inserting NULL."""
    resp = await client.post(
        "/api/v1/transactions",
        json={"amount": 5.0, "merchant": "Uber", "category": "Transport", "raw_input": "Uber $5"},
    )
    assert resp.status_code == 201
    assert resp.json()["occurred_at"]


async def test_notifier_sends_buttons_to_each_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Telegram message carries Change Category / Undo buttons wired to the bot's callbacks."""
    monkeypatch.setattr(settings, "telegram_bot_token", "123:abc")
    monkeypatch.setattr(settings, "telegram_allowed_user_ids", "111,222")
    txn = Transaction(
        id=uuid.uuid4(), amount=Decimal("6.45"), merchant="Star_bucks", category="Food & Drink"
    )

    http = MagicMock()
    http.post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
    http.__aenter__ = AsyncMock(return_value=http)
    http.__aexit__ = AsyncMock(return_value=None)
    with patch("app.services.telegram.httpx.AsyncClient", return_value=http):
        await notify_auto_logged(txn, needs_review=True)

    assert [c.kwargs["json"]["chat_id"] for c in http.post.await_args_list] == [111, 222]
    payload = http.post.await_args.kwargs["json"]
    assert "parse_mode" not in payload  # plain text: underscores in merchants are safe
    assert "check the category" in payload["text"]
    buttons = payload["reply_markup"]["inline_keyboard"][0]
    assert buttons[0]["callback_data"] == f"change_cat_saved:{txn.id}"
    assert buttons[1]["callback_data"] == f"delete:{txn.id}"


async def test_notifier_skips_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    """No owner IDs configured means no HTTP call at all."""
    monkeypatch.setattr(settings, "telegram_allowed_user_ids", "")
    with patch("app.services.telegram.httpx.AsyncClient") as client_cls:
        await notify_auto_logged(MagicMock(), needs_review=False)
    client_cls.assert_not_called()
