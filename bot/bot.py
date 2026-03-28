"""
Telegram bot — Phase 2.

This bot will let you log expenses by sending natural language messages
to a Telegram chat, e.g.:
    "12 chipotle"         → POST /api/v1/transactions
    "spent 8.50 coffee"   → POST /api/v1/transactions
    "/summary"            → GET  /api/v1/summary

The bot uses python-telegram-bot and calls the FastAPI backend over HTTP.

Phase 2 implementation plan:
    1. Parse the user's message to extract amount and raw description
    2. POST to the backend, which handles AI categorization
    3. Reply to the user with a confirmation: "✅ $12 → Chipotle (food)"
    4. Support a /summary command that returns the current month's totals
    5. Support a /undo command to delete the last transaction
"""

import logging

# TODO (Phase 2): import python-telegram-bot
# from telegram import Update
# from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update, context):
    """Handle the /start command — send a welcome message."""
    # TODO (Phase 2): Send welcome message explaining how to use the bot
    pass


async def handle_message(update, context):
    """
    Handle a free-text expense message like "12 chipotle".

    TODO (Phase 2):
        1. Parse amount from the message text (look for a number)
        2. Use the rest of the text as raw_input
        3. POST to http://backend:8000/api/v1/transactions
        4. Reply with a formatted confirmation
    """
    pass


async def summary_command(update, context):
    """
    Handle the /summary command.

    TODO (Phase 2):
        1. GET http://backend:8000/api/v1/summary
        2. Format the response as a readable message
        3. Send it back to the user
    """
    pass


if __name__ == "__main__":
    # TODO (Phase 2): Build and run the application
    # app = ApplicationBuilder().token(BOT_TOKEN).build()
    # app.add_handler(CommandHandler("start", start))
    # app.add_handler(CommandHandler("summary", summary_command))
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # app.run_polling()
    logger.info("Bot stub — Phase 2 not yet implemented")
