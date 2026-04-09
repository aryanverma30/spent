"""Telegram bot for Spent — log expenses with natural language, powered by Claude AI."""
import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
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

CATEGORIES = [
    "Food & Drink",
    "Transport",
    "Entertainment",
    "Shopping",
    "Health",
    "Utilities",
    "Travel",
    "Pets",
    "Other",
]

CATEGORY_EMOJIS = {
    "Food & Drink": "🍔",
    "Transport": "🚗",
    "Entertainment": "🎬",
    "Shopping": "🛍️",
    "Health": "💊",
    "Utilities": "💡",
    "Travel": "✈️",
    "Pets": "🐾",
    "Other": "📦",
}


async def api_post(path: str, data: dict) -> Optional[dict]:
    """POST to the backend API and return the JSON response, or None on error."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{BACKEND_URL}/api/v1{path}", json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"API POST {path} failed: {e}")
            return None


async def api_get(path: str, params: dict | None = None) -> Optional[dict | list]:
    """GET from the backend API and return the JSON response, or None on error."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(f"{BACKEND_URL}/api/v1{path}", params=params or {})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"API GET {path} failed: {e}")
            return None


async def api_delete(path: str) -> bool:
    """DELETE from the backend API. Returns True on success."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.delete(f"{BACKEND_URL}/api/v1{path}")
            return resp.status_code == 204
        except Exception as e:
            logger.error(f"API DELETE {path} failed: {e}")
            return False


async def api_patch(path: str, data: dict) -> Optional[dict]:
    """PATCH to the backend API and return the JSON response, or None on error."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.patch(f"{BACKEND_URL}/api/v1{path}", json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"API PATCH {path} failed: {e}")
            return None


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
        "I'll use AI to categorize it and save it automatically.\n\n"
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
        await update.message.reply_text("No transactions found yet. Start logging with a message like `$12 Chipotle`!", parse_mode="Markdown")
        return

    lines = ["📋 *Recent Transactions:*\n"]
    for t in transactions:
        emoji = CATEGORY_EMOJIS.get(t["category"], "📦")
        lines.append(
            f"{emoji} *{t['merchant']}* — ${float(t['amount']):.2f}\n"
            f"   _{t['category']}_ • {t['created_at'][:10]}"
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
# Message Handler (core expense logging flow)
# ---------------------------------------------------------------------------


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages — parse with AI and log the transaction."""
    raw_input = update.message.text.strip()

    # Step 1: Parse with AI
    parsed = await api_post("/ai/parse", {"raw_input": raw_input})
    if not parsed:
        await update.message.reply_text(
            "❌ Backend error. Make sure the backend is running."
        )
        return

    if parsed.get("error") == "not_a_transaction":
        await update.message.reply_text(
            "🤷 Couldn't parse that as a transaction.\n\n"
            "Try: `$12 Chipotle` or `Uber $22` or `Groceries $45`",
            parse_mode="Markdown",
        )
        return

    amount = parsed.get("amount", 0)
    merchant = parsed.get("merchant", "Unknown")
    category = parsed.get("category", "Other")
    confidence = parsed.get("confidence", 0.0)

    # Step 2: High confidence — save automatically
    if confidence >= AI_CONFIDENCE_THRESHOLD:
        saved = await api_post("/transactions", {
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "raw_input": raw_input,
            "ai_confidence": confidence,
        })
        if not saved:
            await update.message.reply_text("❌ Failed to save transaction. Try again.")
            return

        emoji = CATEGORY_EMOJIS.get(category, "📦")
        text = (
            f"✅ *Logged!* Widget will refresh shortly ✓\n\n"
            f"🏦 Merchant:  {merchant}\n"
            f"💰 Amount:   ${float(amount):.2f}\n"
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
        # Step 3: Low confidence — ask for confirmation
        emoji = CATEGORY_EMOJIS.get(category, "📦")
        text = (
            f"🤔 *Is this right?*\n\n"
            f"🏦 Merchant:  {merchant}\n"
            f"💰 Amount:   ${float(amount):.2f}\n"
            f"{emoji} Category: {category}\n"
            f"📊 Confidence: {confidence:.0%}"
        )
        # Store parsed data in context for later use
        context.user_data["pending"] = {
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "raw_input": raw_input,
            "ai_confidence": confidence,
        }
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
                InlineKeyboardButton("🏷 Change Category", callback_data="change_category"),
            ]
        ])
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Callback Query Handler (inline button presses)
# ---------------------------------------------------------------------------


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # Delete a transaction
    if data.startswith("delete:"):
        transaction_id = data.split(":", 1)[1]
        success = await api_delete(f"/transactions/{transaction_id}")
        if success:
            await query.edit_message_text("🗑 Transaction deleted.")
        else:
            await query.edit_message_text("❌ Could not delete transaction.")

    # Confirm a pending transaction
    elif data == "confirm":
        pending = context.user_data.get("pending")
        if not pending:
            await query.edit_message_text("❌ No pending transaction found.")
            return
        saved = await api_post("/transactions", pending)
        if saved:
            emoji = CATEGORY_EMOJIS.get(pending["category"], "📦")
            await query.edit_message_text(
                f"✅ *Logged!*\n\n"
                f"🏦 {pending['merchant']} — ${float(pending['amount']):.2f}\n"
                f"{emoji} {pending['category']}",
                parse_mode="Markdown",
            )
            context.user_data.pop("pending", None)
        else:
            await query.edit_message_text("❌ Failed to save. Try again.")

    # Show category picker for an ALREADY SAVED transaction (change_cat_saved:{id})
    elif data.startswith("change_cat_saved:"):
        transaction_id = data.split(":", 1)[1]
        buttons = []
        row = []
        for i, cat in enumerate(CATEGORIES):
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

    # Apply a category update to an already-saved transaction via PATCH
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

    # Show category picker
    elif data == "change_category":
        buttons = []
        row = []
        for i, cat in enumerate(CATEGORIES):
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

    # Set a specific category for the pending transaction
    elif data.startswith("set_cat:"):
        new_category = data.split(":", 1)[1]
        pending = context.user_data.get("pending")
        if not pending:
            await query.edit_message_text("❌ No pending transaction found.")
            return
        pending["category"] = new_category
        saved = await api_post("/transactions", pending)
        if saved:
            emoji = CATEGORY_EMOJIS.get(new_category, "📦")
            await query.edit_message_text(
                f"✅ *Logged with updated category!*\n\n"
                f"🏦 {pending['merchant']} — ${float(pending['amount']):.2f}\n"
                f"{emoji} {new_category}",
                parse_mode="Markdown",
            )
            context.user_data.pop("pending", None)
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

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("insights", insights_command))
    app.add_handler(CommandHandler("delete", delete_command))

    # Inline button callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Plain text messages (expense logging)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Spent bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
