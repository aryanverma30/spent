"""AI service for parsing transactions and generating insights using Claude."""
import json
import logging

import anthropic

from app.config import settings

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


PARSE_SYSTEM_PROMPT = """You are a personal finance assistant. Today's date is {TODAY}.

Determine whether the user's message is a spending entry, a spending query, or neither.

─── SPENDING ENTRY ────────────────────────────────────────────────────────────
If the message records a purchase (e.g. "$12 Chipotle", "Uber $22", "groceries $45"):
Return ONLY: {"amount": float, "merchant": string, "category": string, "confidence": float}

Allowed categories — use EXACTLY one of these strings:
Food & Drink, Groceries, Transport, Entertainment, Shopping, Health, Housing, Travel, Pets, Other

Category rules:
- "groceries", "grocery", "supermarket", "whole foods", "trader joes", "aldi", "costco" → Groceries
- "restaurant", "coffee", "cafe", "bar", "doordash", "uber eats", "grubhub", "chipotle", "mcdonald" → Food & Drink
- "uber", "lyft", "gas", "parking", "transit", "metro", "taxi" → Transport
- "rent", "mortgage", "utilities", "electric", "water", "internet", "wifi" → Housing
- amount must be a positive float (strip $ signs)
- merchant should be a clean, capitalized name
- confidence is 0-1 representing how sure you are

─── SPENDING QUERY ─────────────────────────────────────────────────────────────
If the message asks about spending for any date or period — past OR current — return a spending query.
This includes: "how much did I spend", "show me my spending", "summary", "what did I spend", "spending for".

Return ONLY: {"type": "spending_query", "period": "daily"|"weekly"|"monthly", "date": "YYYY-MM-DD"}

Examples:
- "how much did I spend on May 4th" → {"type": "spending_query", "period": "daily", "date": "2026-05-04"}
- "show me May 4th spending" → {"type": "spending_query", "period": "daily", "date": "2026-05-04"}
- "weekly spending of May 4th" → {"type": "spending_query", "period": "weekly", "date": "2026-05-04"}
- "spending for April" → {"type": "spending_query", "period": "monthly", "date": "2026-04-01"}
- "show me my monthly summary for May" → {"type": "spending_query", "period": "monthly", "date": "2026-05-01"}
- "May spending" → {"type": "spending_query", "period": "monthly", "date": "2026-05-01"}
- Use the first day of the month as date for monthly queries.
- Use the current year if not specified.

─── UNRECOGNIZED ───────────────────────────────────────────────────────────────
If the message is neither a spending entry nor a spending query:
Return ONLY: {"error": "not_a_transaction"}

Return ONLY the JSON object, no other text."""

INSIGHTS_SYSTEM_PROMPT = """You are a friendly personal finance coach. Given the user's spending breakdown,
write a 2-3 sentence summary. Be specific with numbers. Be encouraging but honest.
Do not use bullet points."""


async def parse_transaction(raw_input: str) -> dict:
    """Parse a natural language spending message into structured data using Claude.

    Also detects spending queries (e.g. "how much did I spend on May 4th") and
    returns {"type": "spending_query", "period": ..., "date": ...} for those.

    Raises RuntimeError if the API key is missing, the Anthropic API call
    fails, or the model returns non-JSON output.  Callers should catch
    RuntimeError and surface a user-friendly message.
    """
    from datetime import date
    today = date.today().isoformat()
    system = PARSE_SYSTEM_PROMPT.replace("{TODAY}", today)

    client = get_client()
    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=system,
            messages=[{"role": "user", "content": raw_input}],
        )
    except anthropic.APIError as exc:
        logger.error("Anthropic API error in parse_transaction: %s", exc)
        raise RuntimeError(f"AI service unavailable: {exc}") from exc

    text = next(block.text for block in message.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("Claude returned non-JSON in parse_transaction: %r", text)
        raise RuntimeError(f"AI returned an unexpected response format: {exc}") from exc


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
