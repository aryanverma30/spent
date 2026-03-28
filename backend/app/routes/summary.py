"""
Summary route — Phase 3.

Will return a breakdown of spending by category for a given time period,
suitable for rendering a donut/pie chart in the widget.

Example future response:
    {
        "period": "2024-01",
        "total": 450.00,
        "categories": [
            {"category": "food", "total": 200.00, "percentage": 44.4},
            {"category": "transport", "total": 150.00, "percentage": 33.3},
            ...
        ]
    }
"""

from fastapi import APIRouter

router = APIRouter(prefix="/summary", tags=["summary"])


@router.get("/")
async def get_summary():
    """Return spending summary grouped by category. (Not yet implemented.)"""
    return {"message": "not implemented"}
