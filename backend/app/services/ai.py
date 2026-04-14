"""AI service for parsing transactions and generating insights using Claude."""

import json
import logging

import anthropic

from app.config import settings
from app.constants import CATEGORIES

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    """Return a cached Anthropic async client (lazy initialization).

    Raises RuntimeError if ANTHROPIC_API_KEY is not configured so callers
    can catch it and return a graceful response instead of a 500.
    """
    global _client
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file or Railway environment variables."
        )
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


PARSE_SYSTEM_PROMPT = """You are a personal finance assistant. Extract spending information from the user's message
and return ONLY valid JSON with this exact schema:
{ "amount": float, "merchant": string, "category": string, "confidence": float }

Allowed categories (use EXACTLY one of these strings):
Food & Drink, Transport, Entertainment, Shopping, Health, Utilities, Travel, Pets, Other

Rules:
- amount must be a positive float (strip $ signs)
- merchant should be a clean, capitalized name
- confidence is 0-1 representing how sure you are
- If the message is not a valid spending entry, return: { "error": "not_a_transaction" }
- Return ONLY the JSON object, no other text"""

INSIGHTS_SYSTEM_PROMPT = """You are a friendly personal finance coach. Given the user's spending breakdown,
write a 2-3 sentence summary. Be specific with numbers. Be encouraging but honest.
Do not use bullet points."""


async def parse_transaction(raw_input: str) -> dict:
    """Parse a natural language spending message into structured data using Claude.

    Raises RuntimeError (from get_client) if API key is not set, or any
    anthropic exception on API failure — callers must handle both.
    """
    client = get_client()
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        system=PARSE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_input}],
    )
    text = next(block.text for block in message.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


async def generate_insights(breakdown: list[dict], days_remaining: int) -> str:
    """Generate a 2-3 sentence spending summary using Claude.

    Returns a plain string.  Falls back to a friendly placeholder if the
    Anthropic API key is missing or the API call fails — never raises.
    """
    if not breakdown:
        return "No spending recorded yet this period. Start logging expenses to see insights!"

    try:
        client = get_client()
    except RuntimeError as e:
        return f"AI insights unavailable: {e}"

    breakdown_text = "\n".join(
        f"- {item['category']}: ${item['total']:.2f} ({item['count']} transactions)"
        for item in breakdown
    )
    user_message = f"Days remaining in period: {days_remaining}\n\nSpending breakdown:\n{breakdown_text}"

    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=INSIGHTS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return next(block.text for block in message.content if block.type == "text").strip()
    except Exception as e:
        return f"Could not generate insights right now ({type(e).__name__}). Try again later."
