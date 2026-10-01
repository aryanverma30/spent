"""Send Telegram messages from the backend (used for auto-logged purchases)."""
import logging

import httpx

from app.config import settings
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

_EMOJIS = {
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


async def notify_auto_logged(transaction: Transaction, needs_review: bool) -> None:
    """Message the owner about an auto-logged purchase, with Change Category / Undo buttons.

    The buttons reuse the bot's existing callback handlers (change_cat_saved:, delete:).
    Failures are logged and swallowed — the transaction is already saved.
    """
    if not settings.telegram_bot_token or not settings.telegram_owner_ids:
        logger.info("Telegram not configured; skipping auto-log notification")
        return

    emoji = _EMOJIS.get(transaction.category, "📦")
    header = "🤔 Auto-logged — check the category?" if needs_review else "✅ Auto-logged"
    # Plain text, not Markdown, so merchant names with _ or * can't break the message.
    text = (
        f"{header}\n\n"
        f"🏦 {transaction.merchant}\n"
        f"💰 ${float(transaction.amount):.2f}\n"
        f"{emoji} {transaction.category}"
    )
    reply_markup = {
        "inline_keyboard": [[
            {"text": "🏷 Change Category", "callback_data": f"change_cat_saved:{transaction.id}"},
            {"text": "↩️ Undo", "callback_data": f"delete:{transaction.id}"},
        ]]
    }

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        for chat_id in settings.telegram_owner_ids:
            try:
                resp = await client.post(
                    url, json={"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                # Don't log exc's URL — it contains the bot token.
                logger.error("Telegram notification to %s failed: %s", chat_id, type(exc).__name__)
