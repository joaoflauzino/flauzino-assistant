#!/usr/bin/env python3
"""Main entry point for the Telegram bot."""

import signal
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from telegram_api.settings import settings
from telegram_api.core.logger import get_logger
from telegram_api.core.http_client import close_http_client
from telegram_api.handlers.command_handler import start_command, help_command
from telegram_api.handlers.message_handler import handle_text_message
from telegram_api.handlers.photo_handler import handle_photo_message


logger = get_logger(__name__)


def main() -> None:
    """Start the Telegram bot."""
    logger.info("Starting Telegram bot...")

    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Register photo handler (before text handler to prioritize photos)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))

    # Register text message handler
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    logger.info("Handlers registered successfully")

    # Handle graceful shutdown
    async def shutdown(application):
        """Cleanup on shutdown."""
        logger.info("Shutting down, cleaning up resources...")
        await close_http_client()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the bot (polling mode)
    logger.info(
        f"Bot started. Polling Telegram for updates and forwarding to agent_api: {settings.AGENT_API_URL}"
    )

    # Register shutdown handler with application
    application.post_shutdown = shutdown

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
