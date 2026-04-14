"""Bot-side constants that mirror backend/app/constants.py.

The bot runs in a separate Docker container and cannot import from the backend
package directly, so this file keeps a copy of the shared constants.
If you change CATEGORIES or CATEGORY_COLORS, update both files together.
"""

CATEGORIES: list[str] = [
    "Food & Drink",
    "Groceries",
    "Transport",
    "Entertainment",
    "Shopping",
    "Health",
    "Housing",
    "Travel",
    "Pets",
    "Other",
]
