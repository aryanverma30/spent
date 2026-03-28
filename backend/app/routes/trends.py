"""
Trends route — Phase 3.

Will return spending over time (daily/weekly/monthly) so the widget and
frontend can render a line or bar chart showing whether spending is
increasing or decreasing.

Example future response:
    {
        "interval": "weekly",
        "data": [
            {"week": "2024-W01", "total": 123.45},
            {"week": "2024-W02", "total": 98.00},
            ...
        ]
    }
"""

from fastapi import APIRouter

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/")
async def get_trends():
    """Return spending trends over time. (Not yet implemented.)"""
    return {"message": "not implemented"}
