"""Telegram bot for Spent — log expenses with natural language, powered by Claude AI."""
import logging
import os
from io import BytesIO
from typing import Optional

import httpx
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.helpers import escape_markdown
from telegram.ext import (
    ApplicationBuilder,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
AI_CONFIDENCE_THRESHOLD = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.75"))
API_TOKEN = os.getenv("API_TOKEN", "")
# Comma-separated Telegram user IDs allowed to use the bot. Anyone else is ignored.
ALLOWED_USER_IDS = {
    int(uid) for uid in os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").split(",") if uid.strip()
}

from constants import CATEGORIES  # noqa: E402 — mirrors backend/app/constants.py

CATEGORY_EMOJIS = {
    "Food & Drink": "🍔",
    "Groceries": "🌱",
    "Transport": "🚗",
    "Entertainment": "🎬",
    "Shopping": "🛍️",
    "Health": "💊",
    "Housing": "🏠",
    "Travel": "✈️",
    "Pets": "🐾",
    "Other": "📦",
}


def _client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Return an HTTP client that sends the backend API token on every request."""
    headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}
    return httpx.AsyncClient(base_url=f"{BACKEND_URL}/api/v1", headers=headers, timeout=timeout)


def md(text: object) -> str:
    """Escape user-supplied text (merchant names) for parse_mode="Markdown" messages."""
    return escape_markdown(str(text), version=1)


async def api_post(path: str, data: dict, timeout: float = 30.0) -> Optional[dict]:
    """POST to the backend API and return the JSON response, or None on error."""
    async with _client(timeout) as client:
        try:
            resp = await client.post(path, json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("API POST %s failed: %s", path, e)
            return None


async def api_get(path: str, params: dict | None = None) -> Optional[dict | list]:
    """GET from the backend API and return the JSON response, or None on error."""
    async with _client() as client:
        try:
            resp = await client.get(path, params=params or {})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("API GET %s failed: %s", path, e)
            return None


async def api_get_bytes(path: str, params: dict | None = None) -> Optional[bytes]:
    """GET from the backend API and return raw bytes, or None on error."""
    async with _client() as client:
        try:
            resp = await client.get(path, params=params or {})
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            logger.error("API GET bytes %s failed: %s", path, e)
            return None


async def api_delete(path: str) -> bool:
    """DELETE from the backend API. Returns True on success."""
    async with _client() as client:
        try:
            resp = await client.delete(path)
            return resp.status_code == 204
        except Exception as e:
            logger.error("API DELETE %s failed: %s", path, e)
            return False


async def api_patch(path: str, data: dict) -> Optional[dict]:
    """PATCH to the backend API and return the JSON response, or None on error."""
    async with _client() as client:
        try:
            resp = await client.patch(path, json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("API PATCH %s failed: %s", path, e)
            return None


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


async def restrict_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Drop every update that doesn't come from an allowed user (runs before all handlers)."""
    user = update.effective_user
    if user is not None and user.id in ALLOWED_USER_IDS:
        return
    # Logged so the owner can find their own ID when first setting up the bot.
    logger.warning(
        "Ignoring update from unauthorized user id=%s (add it to TELEGRAM_ALLOWED_USER_IDS if this is you)",
        user.id if user else None,
    )
    raise ApplicationHandlerStop


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message with usage instructions."""
    text = (
        "👋 *Welcome to Spent!*\n\n"
        "Track your spending by sending me a message like:\n"
        "  • `$12 Chipotle`\n"
        "  • `Uber $22`\n"
        "  • `Bought groceries for $45`\n\n"
        "You can also ask about your spending:\n"
        "  • `How much did I spend on May 4th?`\n"
        "  • `Spending for April`\n"
        "  • `Top 5 purchases this month`\n"
        "  • `How much more on food than last month?`\n\n"
        "*Commands:*\n"
        "/history — your last 10 transactions\n"
        "/summary — this month's spending by category\n"
        "/insights — AI-generated spending insights\n"
        "/delete — delete recent transactions\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the last 10 transactions."""
    transactions = await api_get("/transactions", {"limit": 10})
    if not transactions:
        await update.message.reply_text(
            "No transactions found yet. Start logging with a message like `$12 Chipotle`!",
            parse_mode="Markdown",
        )
        return

    lines = ["📋 *Recent Transactions:*\n"]
    for t in transactions:
        emoji = CATEGORY_EMOJIS.get(t["category"], "📦")
        lines.append(
            f"{emoji} *{md(t['merchant'])}* — ${float(t['amount']):.2f}\n"
            f"   _{t['category']}_ • {t['occurred_at'][:10]}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show this month's spending breakdown by category."""
    data = await api_get("/summary", {"period": "monthly"})
    if not data:
        await update.message.reply_text("Couldn't fetch summary. Is the backend running?")
        return

    lines = [f"📊 *Monthly Summary* — Total: ${data['total_spent']:.2f}\n"]
    for item in data.get("breakdown", []):
        emoji = CATEGORY_EMOJIS.get(item["category"], "📦")
        pct = (item["total"] / data["total_spent"] * 100) if data["total_spent"] > 0 else 0
        lines.append(
            f"{emoji} *{item['category']}*: ${item['total']:.2f} "
            f"({item['count']} transactions, {pct:.0f}%)"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def insights_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show AI-generated spending insights."""
    await update.message.reply_text("🤔 Generating insights...")
    data = await api_get("/insights")
    if not data:
        await update.message.reply_text("Couldn't generate insights. Is the backend running?")
        return
    await update.message.reply_text(f"💡 {data['summary']}")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the last 5 transactions with Delete buttons."""
    transactions = await api_get("/transactions", {"limit": 5})
    if not transactions:
        await update.message.reply_text("No transactions to delete.")
        return

    await update.message.reply_text("Select a transaction to delete:")
    for t in transactions:
        emoji = CATEGORY_EMOJIS.get(t["category"], "📦")
        text = f"{emoji} {t['merchant']} — ${float(t['amount']):.2f} ({t['category']})"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Delete", callback_data=f"delete:{t['id']}")]
        ])
        await update.message.reply_text(text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Spending query handler
# ---------------------------------------------------------------------------


_PERIOD_LABELS = {
    "daily": "on",
    "weekly": "week of",
    "monthly": "for",
}


async def handle_spending_query(
    update: Update, period: str, date: str
) -> None:
    """Fetch and display a donut chart + breakdown + transaction list for a given period."""
    await update.message.reply_text("📊 Fetching your spending data…")

    params = {"period": period, "date": date}

    data = await api_get("/summary", params)
    if not data or data.get("total_spent", 0) == 0:
        preposition = _PERIOD_LABELS.get(period, "for")
        await update.message.reply_text(f"No spending recorded {preposition} {date}.")
        return

    chart_bytes = await api_get_bytes("/charts/donut", params)
    transactions = await api_get("/transactions", {**params, "limit": 50})

    preposition = _PERIOD_LABELS.get(period, "for")
    if period == "monthly":
        display_date = date[:7]
    else:
        display_date = date

    lines = [f"📊 *Spending {preposition} {display_date}* — Total: ${data['total_spent']:.2f}\n"]
    for item in data.get("breakdown", []):
        emoji = CATEGORY_EMOJIS.get(item["category"], "📦")
        pct = (item["total"] / data["total_spent"] * 100) if data["total_spent"] > 0 else 0
        lines.append(
            f"{emoji} *{item['category']}*: ${item['total']:.2f} "
            f"({item['count']} txn, {pct:.0f}%)"
        )

    if transactions:
        lines.append("\n*Transactions:*")
        for t in transactions:
            emoji = CATEGORY_EMOJIS.get(t["category"], "📦")
            lines.append(f"{emoji} {md(t['merchant'])} — ${float(t['amount']):.2f}")

    caption = "\n".join(lines)

    # Telegram captions max out at 1024 chars; truncate gracefully
    if len(caption) > 1020:
        caption = caption[:1020] + "…"

    if chart_bytes:
        await update.message.reply_photo(
            photo=BytesIO(chart_bytes),
            caption=caption,
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(caption, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Message Handler (core expense logging flow)
# ---------------------------------------------------------------------------


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages — parse with AI and log the transaction or answer a query."""
    raw_input = update.message.text.strip()

    parsed = await api_post("/ai/parse", {"raw_input": raw_input})
    if not parsed:
        await update.message.reply_text(
            "❌ Backend error. Make sure the backend is running."
        )
        return

    if parsed.get("type") == "spending_query":
        await handle_spending_query(
            update,
            period=parsed["period"],
            date=parsed["date"],
        )
        return

    if parsed.get("type") == "question":
        await update.message.chat.send_action(ChatAction.TYPING)
        # Answering can take several Claude round-trips, so allow longer than usual.
        result = await api_post("/ai/ask", {"question": raw_input}, timeout=90.0)
        if not result:
            await update.message.reply_text("❌ Couldn't answer that right now. Try again in a bit.")
            return
        # Plain text (no parse_mode): the answer may contain * or _ in merchant names.
        await update.message.reply_text(result["answer"])
        return

    if parsed.get("error") == "not_a_transaction":
        await update.message.reply_text(
            "🤷 Couldn't parse that as a transaction or spending query.\n\n"
            "To log: `$12 Chipotle` or `Uber $22`\n"
            "To ask: `Top 5 purchases this month`",
            parse_mode="Markdown",
        )
        return

    amount = parsed.get("amount", 0)
    merchant = parsed.get("merchant", "Unknown")
    category = parsed.get("category", "Other")
    confidence = parsed.get("confidence", 0.0)
    occurred_on = parsed.get("occurred_on")  # "YYYY-MM-DD" if a date was mentioned
    date_line = f"📅 Date:      {occurred_on}\n" if occurred_on else ""

    if confidence >= AI_CONFIDENCE_THRESHOLD:
        saved = await api_post("/transactions", {
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "raw_input": raw_input,
            "ai_confidence": confidence,
            "occurred_at": occurred_on,
        })
        if not saved:
            await update.message.reply_text("❌ Failed to save transaction. Try again.")
            return

        emoji = CATEGORY_EMOJIS.get(category, "📦")
        text = (
            f"✅ *Logged!* Widget will refresh shortly ✓\n\n"
            f"🏦 Merchant:  {md(merchant)}\n"
            f"💰 Amount:   ${float(amount):.2f}\n"
            f"{date_line}"
            f"{emoji} Category: {category}"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🏷 Change Category",
                    callback_data=f"change_cat_saved:{saved['id']}",
                ),
                InlineKeyboardButton("↩️ Undo", callback_data=f"delete:{saved['id']}"),
            ]
        ])
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)

    else:
        emoji = CATEGORY_EMOJIS.get(category, "📦")
        text = (
            f"🤔 *Is this right?*\n\n"
            f"🏦 Merchant:  {md(merchant)}\n"
            f"💰 Amount:   ${float(amount):.2f}\n"
            f"{date_line}"
            f"{emoji} Category: {category}\n"
            f"📊 Confidence: {confidence:.0%}"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
                InlineKeyboardButton("🏷 Change Category", callback_data="change_category"),
            ]
        ])
        sent = await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
        # Keyed by this message's id so several unconfirmed expenses don't overwrite each other.
        context.user_data.setdefault("pending", {})[sent.message_id] = {
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "raw_input": raw_input,
            "ai_confidence": confidence,
            "occurred_at": occurred_on,
        }


# ---------------------------------------------------------------------------
# Callback Query Handler (inline button presses)
# ---------------------------------------------------------------------------


def _pending_for(query, context: ContextTypes.DEFAULT_TYPE, remove: bool = False) -> Optional[dict]:
    """Return (and optionally remove) the unconfirmed expense attached to the pressed message."""
    pending = context.user_data.get("pending")
    if not isinstance(pending, dict):
        return None
    if remove:
        return pending.pop(query.message.message_id, None)
    return pending.get(query.message.message_id)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("delete:"):
        transaction_id = data.split(":", 1)[1]
        success = await api_delete(f"/transactions/{transaction_id}")
        if success:
            await query.edit_message_text("🗑 Transaction deleted.")
        else:
            await query.edit_message_text("❌ Could not delete transaction.")

    elif data == "confirm":
        pending = _pending_for(query, context)
        if not pending:
            await query.edit_message_text("❌ No pending transaction found.")
            return
        saved = await api_post("/transactions", pending)
        if saved:
            emoji = CATEGORY_EMOJIS.get(pending["category"], "📦")
            await query.edit_message_text(
                f"✅ *Logged!*\n\n"
                f"🏦 {md(pending['merchant'])} — ${float(pending['amount']):.2f}\n"
                f"{emoji} {pending['category']}",
                parse_mode="Markdown",
            )
            _pending_for(query, context, remove=True)
        else:
            await query.edit_message_text("❌ Failed to save. Try again.")

    elif data.startswith("change_cat_saved:"):
        transaction_id = data.split(":", 1)[1]
        buttons = []
        row = []
        for cat in CATEGORIES:
            emoji = CATEGORY_EMOJIS.get(cat, "📦")
            row.append(
                InlineKeyboardButton(
                    f"{emoji} {cat}",
                    callback_data=f"patch_cat:{transaction_id}:{cat}",
                )
            )
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        await query.edit_message_text(
            "Choose a new category:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif data.startswith("patch_cat:"):
        _, transaction_id, new_category = data.split(":", 2)
        updated = await api_patch(f"/transactions/{transaction_id}", {"category": new_category})
        if updated:
            emoji = CATEGORY_EMOJIS.get(new_category, "📦")
            await query.edit_message_text(
                f"✓ Updated to {emoji} *{new_category}*",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text("❌ Could not update category. Try again.")

    elif data == "change_category":
        buttons = []
        row = []
        for cat in CATEGORIES:
            emoji = CATEGORY_EMOJIS.get(cat, "📦")
            row.append(InlineKeyboardButton(f"{emoji} {cat}", callback_data=f"set_cat:{cat}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        await query.edit_message_text(
            "Choose a category:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif data.startswith("set_cat:"):
        new_category = data.split(":", 1)[1]
        pending = _pending_for(query, context)
        if not pending:
            await query.edit_message_text("❌ No pending transaction found.")
            return
        pending["category"] = new_category
        saved = await api_post("/transactions", pending)
        if saved:
            await api_post("/ai/learn", {
                "merchant": pending["merchant"],
                "category": new_category,
            })
            emoji = CATEGORY_EMOJIS.get(new_category, "📦")
            await query.edit_message_text(
                f"✅ *Logged with updated category!*\n\n"
                f"🏦 {md(pending['merchant'])} — ${float(pending['amount']):.2f}\n"
                f"{emoji} {new_category}",
                parse_mode="Markdown",
            )
            _pending_for(query, context, remove=True)
        else:
            await query.edit_message_text("❌ Failed to save. Try again.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the Telegram bot with long polling."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Bot cannot start.")
        return

    if not ALLOWED_USER_IDS:
        logger.warning(
            "TELEGRAM_ALLOWED_USER_IDS is not set — the bot will ignore everyone. "
            "Message the bot once, copy your id from the log, and set it."
        )

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Group -1 runs before the default group 0, so unauthorized updates never reach a handler.
    app.add_handler(TypeHandler(Update, restrict_to_owner), group=-1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("insights", insights_command))
    app.add_handler(CommandHandler("delete", delete_command))

    app.add_handler(CallbackQueryHandler(handle_callback))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Spent bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
