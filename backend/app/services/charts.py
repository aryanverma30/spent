"""Chart generation (Matplotlib headless) and period utility functions."""
import io
from datetime import date as _date
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use("Agg")  # Must be called before importing pyplot — headless rendering
import matplotlib.pyplot as plt

from app.constants import CATEGORY_COLORS, LOCAL_TZ


def get_period_bounds(period: str, date: str | None = None) -> tuple[datetime, datetime]:
    """Return (start, end) UTC datetimes for daily/weekly/monthly periods.

    If date is None, uses today. For both cases the natural end of the period
    is computed (e.g. end of the day, end of the week, end of the month) and
    then capped at now+1s so in-progress periods don't show a future end time.

    - daily:   midnight-to-midnight in America/Chicago (CST/CDT)
    - weekly:  Monday 00:00 to Sunday 23:59:59 (ISO weeks, run Monday–Sunday)
    - monthly: 1st of month 00:00 to 1st of next month 00:00
    """
    now = datetime.now(timezone.utc)

    if date is None:
        target_local = now.astimezone(LOCAL_TZ)
    else:
        d = _date.fromisoformat(date)
        target_local = datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=LOCAL_TZ)

    if period == "daily":
        local_midnight = target_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start = local_midnight.astimezone(timezone.utc)
        natural_end = (local_midnight + timedelta(days=1)).astimezone(timezone.utc)

    elif period == "weekly":
        # Weeks run Monday–Sunday (ISO week).
        # weekday(): 0=Mon … 6=Sun → days since last Monday = weekday()
        days_since_monday = target_local.weekday()
        monday_local = (target_local - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start = monday_local.astimezone(timezone.utc)
        natural_end = (monday_local + timedelta(days=7)).astimezone(timezone.utc)

    else:  # monthly
        month_start_local = target_local.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        start = month_start_local.astimezone(timezone.utc)
        if month_start_local.month == 12:
            next_month = month_start_local.replace(year=month_start_local.year + 1, month=1)
        else:
            next_month = month_start_local.replace(month=month_start_local.month + 1)
        natural_end = next_month.astimezone(timezone.utc)

    # Cap end at now+1s so current periods don't include future time
    end = min(natural_end, now + timedelta(seconds=1))
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
