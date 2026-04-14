"""Shared constants for categories and chart colours.

This is the single source of truth for the category list and colour palette
used by the AI service, the insights route, and the chart generator.
bot/constants.py mirrors this file for the Telegram bot (separate container).
"""

CATEGORIES: list[str] = [
    "Food & Drink",
    "Groceries",
    "Transport",
    "Entertainment",
    "Shopping",
    "Health",
    "Utilities",
    "Travel",
    "Pets",
    "Other",
]

CATEGORY_COLORS: dict[str, str] = {
    "Food & Drink": "#FF6B6B",
    "Groceries": "#52B788",
    "Transport": "#4ECDC4",
    "Entertainment": "#45B7D1",
    "Shopping": "#96CEB4",
    "Health": "#FFEAA7",
    "Utilities": "#DDA0DD",
    "Travel": "#F0A500",
    "Pets": "#F8C8D4",
    "Other": "#B0BEC5",
}
