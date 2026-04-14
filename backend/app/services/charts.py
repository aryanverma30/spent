"""Chart generation (Matplotlib headless) and period utility functions."""
import io
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")  # Must be called before importing pyplot — headless rendering
import matplotlib.pyplot as plt

from app.constants import CATEGORY_COLORS


_CHICAGO = ZoneInfo("America/Chicago")


def get_period_bounds(period: str) -> tuple[datetime, datetime]:
    """Return (start, end) UTC datetimes for daily/weekly/monthly periods.

    - daily:   midnight-to-midnight in America/Chicago (CST/CDT)
    - weekly:  from Monday 00:00 UTC of the current ISO week to now
    - monthly: from 00:00 UTC on the 1st of the current calendar month to now

    end is bumped by 1 second so that a transaction inserted at the exact
    moment the query is built is never excluded by a strict < comparison.
    """
    now = datetime.now(timezone.utc)
    end = now + timedelta(seconds=1)   # inclusive upper bound

    if period == "daily":
        # Compute local midnight in America/Chicago, then convert back to UTC
        now_local = now.astimezone(_CHICAGO)
        local_midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start = local_midnight.astimezone(timezone.utc)
    elif period == "weekly":
        # weekday() returns 0=Monday … 6=Sunday — subtracting it always
        # lands on the Monday that started the current ISO week.
        days_since_monday = now.weekday()  # 0 on Monday, 6 on Sunday
        start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:  # monthly
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return start, end


def generate_donut_chart(breakdown: list[dict]) -> bytes:
    """Generate a donut chart PNG from a spending breakdown list.

    Each item in breakdown must have 'category' and 'total' keys.
    Returns raw PNG bytes suitable for streaming as image/png.
    """
    fig, ax = plt.subplots(figsize=(4, 4), dpi=150)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    if not breakdown:
        ax.text(
            0.5, 0.5, "No data",
            ha="center", va="center",
            transform=ax.transAxes,
            color="white", fontsize=12,
        )
        ax.axis("off")
    else:
        labels = [item["category"] for item in breakdown]
        values = [float(item["total"]) for item in breakdown]
        colors = [CATEGORY_COLORS.get(cat, "#B0BEC5") for cat in labels]

        ax.pie(
            values,
            labels=None,
            colors=colors,
            wedgeprops={"width": 0.5, "linewidth": 0},
            startangle=90,
        )

        total = sum(values)
        ax.text(
            0, 0, f"${total:.0f}",
            ha="center", va="center",
            fontsize=14, fontweight="bold", color="white",
        )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", facecolor="none", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
