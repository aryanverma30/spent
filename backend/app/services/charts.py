"""Chart generation (Matplotlib headless) and period utility functions."""
import io
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use("Agg")  # Must be called before importing pyplot — headless rendering
import matplotlib.pyplot as plt

CATEGORY_COLORS: dict[str, str] = {
    "Food & Drink": "#FF6B6B",
    "Transport": "#4ECDC4",
    "Entertainment": "#45B7D1",
    "Shopping": "#96CEB4",
    "Health": "#FFEAA7",
    "Utilities": "#DDA0DD",
    "Travel": "#F0A500",
    "Other": "#B0BEC5",
}


def get_period_bounds(period: str) -> tuple[datetime, datetime]:
    """Return (start, end) UTC datetimes for daily/weekly/monthly periods.

    - daily:   from midnight UTC today to now
    - weekly:  from Monday 00:00 UTC of the current ISO week to now
    - monthly: from 00:00 UTC on the 1st of the current calendar month to now

    end is bumped by 1 second so that a transaction inserted at the exact
    moment the query is built is never excluded by a strict < comparison.
    """
    now = datetime.now(timezone.utc)
    end = now + timedelta(seconds=1)   # inclusive upper bound

    if period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        # weekday() is 0=Monday … 6=Sunday, so this always gives Monday 00:00
        days_since_monday = now.weekday()
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


def generate_trend_chart(buckets: list[dict]) -> bytes:
    """Generate a horizontal bar chart PNG from spending trend buckets.

    Each bucket must have 'label' (str) and 'total' (float) keys.
    Returns raw PNG bytes suitable for streaming as image/png.
    """
    fig, ax = plt.subplots(figsize=(5, max(3, len(buckets) * 0.4 + 1)), dpi=150)
    fig.patch.set_facecolor("#1A1A2E")
    ax.set_facecolor("#1A1A2E")

    if not buckets:
        ax.text(
            0.5, 0.5, "No data",
            ha="center", va="center",
            transform=ax.transAxes,
            color="white", fontsize=12,
        )
        ax.axis("off")
    else:
        labels = [b["label"] for b in buckets]
        values = [float(b["total"]) for b in buckets]
        y_pos = list(range(len(labels)))

        bars = ax.barh(y_pos, values, color="#4ECDC4", edgecolor="none")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, color="white", fontsize=8)
        ax.tick_params(colors="white", length=0)
        ax.spines[:].set_visible(False)
        ax.xaxis.set_visible(False)

        max_val = max(values) if values else 1.0
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + max_val * 0.02,
                bar.get_y() + bar.get_height() / 2,
                f"${val:.0f}",
                va="center", color="white", fontsize=7,
            )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight",
                facecolor="#1A1A2E", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
