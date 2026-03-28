"""
AI categorization service — Phase 3.

This service will call the Anthropic Claude API to parse a raw expense
string (e.g. "12 chipotle bowl") and return:
  - merchant:       "Chipotle"
  - category:       "food"
  - ai_confidence:  0.95

It will be called from the POST /transactions endpoint when `category`
is not provided in the request body.

Supported categories (to be defined in Phase 3):
    food, transport, entertainment, shopping, health, utilities, other
"""

from app.config import settings  # noqa: F401  (will be used in Phase 3)


async def categorize(raw_input: str) -> dict:
    """
    Use Claude to infer merchant, category, and confidence from raw_input.

    Args:
        raw_input: The raw expense string, e.g. "12 chipotle bowl"

    Returns:
        A dict with keys: merchant, category, ai_confidence

    TODO (Phase 3):
        1. Build a prompt that asks Claude to extract merchant and category
        2. Call the Anthropic API with the prompt
        3. Parse the response JSON
        4. Return the structured result

    For now, returns a placeholder so the service can be imported without error.
    """
    # TODO (Phase 3): Replace with real Claude API call
    return {
        "merchant": raw_input,
        "category": "other",
        "ai_confidence": None,
    }
