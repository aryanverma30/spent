"""
Chart data service — Phase 4.

This service will transform raw transaction data from the database into
chart-friendly data structures that can be consumed by:
  - The Scriptable iOS widget (donut/pie chart of spending by category)
  - The summary endpoint (for future web dashboard)

It will produce output like:
    {
        "labels": ["food", "transport", "shopping"],
        "values": [200.00, 80.00, 45.00],
        "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1"]
    }
"""


def build_donut_chart_data(transactions: list) -> dict:
    """
    Aggregate transactions by category and return chart-ready data.

    Args:
        transactions: List of Transaction ORM objects

    Returns:
        A dict with labels, values, and colors for a donut chart

    TODO (Phase 4):
        1. Group transactions by category and sum amounts
        2. Sort by total descending
        3. Assign a color to each category
        4. Return the structured dict
    """
    # TODO (Phase 4): Implement chart aggregation logic
    return {"labels": [], "values": [], "colors": []}
