"""Answer free-form spending questions with Claude tool use over the transactions table.

Claude gets two read-only query tools and decides which to call (and how many
times) to answer questions like "top 5 purchases this month" or "how much more
did I spend on food than last month?". It never sees or writes SQL.
"""
import json
import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import CATEGORIES, LOCAL_TZ
from app.models.transaction import Transaction
from app.services.ai import get_client
from app.services.budgets import budget_status

logger = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"
MAX_TOOL_ROUNDS = 8  # a question rarely needs more than 2–3; this just stops runaway loops

SYSTEM_PROMPT = """You answer questions about the user's personal spending using the tools provided.

- Always use the tools to get numbers. Never guess or estimate amounts.
- Dates are in the user's local time zone. "This month" means the 1st of the current month through today; "last month" is the full previous calendar month; weeks run Monday–Sunday.
- To compare periods, call a tool once per period.
- Reply in plain text for a Telegram chat: no Markdown, no tables. Short numbered lists are fine.
- Be brief: answer first, then at most a sentence of useful context. Format money as $1,234.56.
- If there is no matching data, say so plainly."""

_DATE = {"type": "string", "format": "date", "description": "YYYY-MM-DD, inclusive, local time"}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "find_transactions",
        "description": (
            "List individual transactions in a date range, optionally filtered by category, "
            "merchant, or minimum amount. Use for 'top N purchases', 'what did I buy at X', "
            "'my biggest expense', or 'when did I last go to X'. Also returns how many "
            "transactions matched in total, beyond the returned page."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": _DATE,
                "end_date": _DATE,
                "category": {"type": "string", "enum": CATEGORIES},
                "merchant_contains": {
                    "type": "string",
                    "description": "Case-insensitive substring of the merchant name",
                },
                "min_amount": {"type": "number"},
                "sort_by": {"type": "string", "enum": ["amount", "date"]},
                "descending": {"type": "boolean"},
                "limit": {"type": "integer", "description": "1–50, default 10"},
            },
            "required": ["start_date", "end_date"],
            "additionalProperties": False,
        },
    },
    {
        "name": "budget_status",
        "description": (
            "This month's budgets: limit, spent, remaining, percent used, daily allowance for "
            "the rest of the month, projected month-end spend, and whether it's on track. "
            "'Total' is the overall budget. Use for 'am I on track', 'how much can I spend', "
            "or anything about budgets. Returns an empty list if no budgets are set."
        ),
        "strict": True,
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "spending_totals",
        "description": (
            "Total, count, and average spend in a date range, grouped by category, merchant, "
            "day, week, or month (or 'none' for a single overall total). Use for 'how much did "
            "I spend on X', comparisons between periods, trends, and 'where does my money go'. "
            "Category and merchant groups are sorted by total, highest first; time groups are "
            "chronological."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": _DATE,
                "end_date": _DATE,
                "group_by": {
                    "type": "string",
                    "enum": ["none", "category", "merchant", "day", "week", "month"],
                },
                "category": {"type": "string", "enum": CATEGORIES},
                "merchant_contains": {
                    "type": "string",
                    "description": "Case-insensitive substring of the merchant name",
                },
            },
            "required": ["start_date", "end_date", "group_by"],
            "additionalProperties": False,
        },
    },
]


class ToolInputError(ValueError):
    """Raised for tool inputs Claude can correct (bad dates, etc.)."""


def _utc_bounds(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    """Convert inclusive local YYYY-MM-DD dates to a [start, end) UTC range."""
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise ToolInputError(f"Dates must be YYYY-MM-DD: {exc}") from exc
    if end < start:
        raise ToolInputError("end_date is before start_date")
    return (
        datetime.combine(start, time.min, LOCAL_TZ).astimezone(timezone.utc),
        datetime.combine(end + timedelta(days=1), time.min, LOCAL_TZ).astimezone(timezone.utc),
    )


def _local(dt: datetime) -> datetime:
    """Convert a stored timestamp to local time (naive values are UTC, as SQLite returns them)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL_TZ)


def _filtered(args: dict[str, Any]):
    """Build the shared SELECT for a date range plus optional category/merchant filters."""
    start, end = _utc_bounds(args["start_date"], args["end_date"])
    query = (
        select(Transaction)
        .where(Transaction.occurred_at >= start)
        .where(Transaction.occurred_at < end)
    )
    if args.get("category"):
        query = query.where(Transaction.category == args["category"])
    if args.get("merchant_contains"):
        query = query.where(Transaction.merchant.ilike(f"%{args['merchant_contains']}%"))
    return query


async def find_transactions(args: dict[str, Any], session: AsyncSession) -> dict[str, Any]:
    """Return matching transactions, sorted and limited, plus the total match count."""
    query = _filtered(args)
    if args.get("min_amount") is not None:
        query = query.where(Transaction.amount >= args["min_amount"])
    rows = list((await session.execute(query)).scalars().all())

    key = (lambda t: float(t.amount)) if args.get("sort_by") == "amount" else (lambda t: _local(t.occurred_at))
    rows.sort(key=key, reverse=args.get("descending", True))
    limit = min(max(int(args.get("limit") or 10), 1), 50)

    return {
        "matched": len(rows),
        "returned": min(limit, len(rows)),
        "transactions": [
            {
                "date": _local(t.occurred_at).date().isoformat(),
                "merchant": t.merchant,
                "category": t.category,
                "amount": round(float(t.amount), 2),
                **({"note": t.note} if t.note else {}),
            }
            for t in rows[:limit]
        ],
    }


def _bucket(t: Transaction, group_by: str) -> str:
    """Return the group key for a transaction."""
    if group_by == "category":
        return t.category
    if group_by == "merchant":
        return t.merchant
    day = _local(t.occurred_at).date()
    if group_by == "day":
        return day.isoformat()
    if group_by == "week":
        return f"week of {(day - timedelta(days=day.weekday())).isoformat()}"
    if group_by == "month":
        return day.strftime("%Y-%m")
    return "all"


async def spending_totals(args: dict[str, Any], session: AsyncSession) -> dict[str, Any]:
    """Aggregate total / count / average per group.

    Grouping happens in Python: a personal ledger is a few thousand rows a year,
    and it keeps local-time day/week/month buckets identical across databases.
    """
    rows = (await session.execute(_filtered(args))).scalars().all()
    group_by = args["group_by"]

    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for t in rows:
        k = _bucket(t, group_by)
        totals[k] += float(t.amount)
        counts[k] += 1

    if group_by in ("category", "merchant", "none"):
        keys = sorted(totals, key=totals.get, reverse=True)
    else:
        keys = sorted(totals)

    grand_total = sum(totals.values())
    return {
        "total": round(grand_total, 2),
        "count": len(rows),
        "groups": [
            {
                "group": k,
                "total": round(totals[k], 2),
                "count": counts[k],
                "average": round(totals[k] / counts[k], 2),
                "share_of_total": f"{totals[k] / grand_total:.0%}" if grand_total else "0%",
            }
            for k in keys
        ] if group_by != "none" else [],
    }


async def get_budget_status(args: dict[str, Any], session: AsyncSession) -> dict[str, Any]:
    """Return this month's budget statuses."""
    return {"budgets": await budget_status(session)}


_HANDLERS = {
    "find_transactions": find_transactions,
    "spending_totals": spending_totals,
    "budget_status": get_budget_status,
}


async def _run_tool(name: str, args: dict[str, Any], session: AsyncSession) -> dict[str, Any]:
    """Execute one tool call and wrap the outcome as a tool_result payload."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"content": f"Unknown tool {name!r}", "is_error": True}
    try:
        result = await handler(args, session)
    except ToolInputError as exc:
        return {"content": str(exc), "is_error": True}
    return {"content": json.dumps(result)}


async def answer_question(question: str, session: AsyncSession) -> str:
    """Answer a natural-language spending question, calling query tools as needed.

    Raises RuntimeError if the AI service is unavailable or misconfigured.
    """
    client = get_client()
    now = datetime.now(LOCAL_TZ)
    # Today's date goes in the user turn, not the system prompt, so the
    # system prompt + tools stay byte-identical (cacheable) across requests.
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": f"Today is {now:%A, %Y-%m-%d}.\n\n{question}"}
    ]

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            response = await client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
                output_config={"effort": "medium"},
                # On a safety-classifier decline, re-run on Anthropic's recommended fallback model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.APIError as exc:
            logger.error("Anthropic API error in answer_question: %s", exc)
            raise RuntimeError(f"AI service unavailable: {exc}") from exc

        if response.stop_reason == "refusal":
            return "Sorry, I can't help with that one."
        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            if response.stop_reason == "max_tokens" and not text:
                return "That answer got too long — try a narrower question."
            return text or "I couldn't come up with an answer to that."

        # Append the full content (thinking + tool_use blocks) unchanged, then all results in one turn.
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                logger.info("assistant tool call %s %s", block.name, block.input)
                outcome = await _run_tool(block.name, block.input, session)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, **outcome})
        messages.append({"role": "user", "content": tool_results})

    logger.warning("answer_question hit MAX_TOOL_ROUNDS for %r", question)
    return "That question needed more digging than I'm allowed to do — try breaking it up."
