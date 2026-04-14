"""Unit tests for services/ai.py — parse_transaction."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from app.services.ai import parse_transaction

pytestmark = pytest.mark.asyncio


def _make_message(text: str) -> MagicMock:
    """Build a minimal mock Anthropic Message object with a single text block."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


async def test_parse_transaction_returns_dict_on_valid_response() -> None:
    """parse_transaction returns the expected dict when Claude responds with valid JSON."""
    valid_json = '{"amount": 12.5, "merchant": "Chipotle", "category": "Food & Drink", "confidence": 0.95}'

    with patch("app.services.ai.get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=_make_message(valid_json))
        mock_get_client.return_value = mock_client

        result = await parse_transaction("$12.50 Chipotle")

    assert result["amount"] == 12.5
    assert result["merchant"] == "Chipotle"
    assert result["category"] == "Food & Drink"
    assert result["confidence"] == 0.95


async def test_parse_transaction_strips_markdown_code_fence() -> None:
    """parse_transaction strips ```json ... ``` fences before parsing."""
    fenced = '```json\n{"amount": 5.0, "merchant": "Starbucks", "category": "Food & Drink", "confidence": 0.9}\n```'

    with patch("app.services.ai.get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=_make_message(fenced))
        mock_get_client.return_value = mock_client

        result = await parse_transaction("$5 Starbucks")

    assert result["merchant"] == "Starbucks"


async def test_parse_transaction_raises_runtime_error_on_json_decode_error() -> None:
    """parse_transaction raises RuntimeError when the model returns non-JSON."""
    with patch("app.services.ai.get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_make_message("Sorry, I cannot parse that.")
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="unexpected response format"):
            await parse_transaction("hello world")


async def test_parse_transaction_raises_runtime_error_on_api_error() -> None:
    """parse_transaction raises RuntimeError when the Anthropic API call fails."""
    with patch("app.services.ai.get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APIStatusError(
                "rate limited",
                response=MagicMock(status_code=429, headers={}),
                body={},
            )
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="AI service unavailable"):
            await parse_transaction("$10 coffee")
