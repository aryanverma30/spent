"""
Insights route — Phase 3.

Will use Claude AI to generate natural-language insights about spending
patterns, e.g. "You spent 30% more on food this week than last week."
These will be surfaced in the Telegram bot and optionally in the widget.

Example future response:
    {
        "insights": [
            "Your food spending is up 30% this week.",
            "You've hit 80% of your monthly transport budget.",
            "Friday is your highest-spending day on average."
        ],
        "generated_at": "2024-01-15T10:30:00Z"
    }
"""

from fastapi import APIRouter

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/")
async def get_insights():
    """Return AI-generated spending insights. (Not yet implemented.)"""
    return {"message": "not implemented"}
