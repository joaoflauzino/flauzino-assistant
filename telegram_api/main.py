"""Main entry point for the Telegram bot."""

import datetime
import signal
import sys
from sqlalchemy import text
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from telegram_api.core.database import close_db, get_db, init_db
from telegram_api.core.http_client import close_http_client, get_balance_graph
from telegram_api.core.logger import get_logger
from telegram_api.core.metrics import (
    TELEGRAM_MESSAGES_RECEIVED_TOTAL,
    start_metrics_server,
)
from telegram_api.handlers.balance_handler import balance_handlers
from telegram_api.handlers.command_handler import help_command, start_command
from telegram_api.handlers.expense_handler import expense_conv_handler
from telegram_api.handlers.message_handler import agent_callback_handler, handle_text_message
from telegram_api.handlers.photo_handler import handle_photo_message
from telegram_api.handlers.voice_handler import handle_voice_message
from telegram_api.settings import settings

logger = get_logger(__name__)


def main() -> None:
    """Start the Telegram bot."""
    logger.info("Starting Telegram bot...")

    # Start Prometheus metrics HTTP server
    start_metrics_server(port=settings.METRICS_PORT)
    logger.info(f"Prometheus metrics server started on port {settings.METRICS_PORT}")

    async def auth_middleware(update: Update, context) -> None:
        """Middleware to check if the user is allowed to use the bot and record metrics."""
        msg_type = "unknown"
        if update.message:
            if update.message.text:
                msg_type = "command" if update.message.text.startswith("/") else "text"
            elif update.message.photo:
                msg_type = "photo"
            elif update.message.voice or update.message.audio:
                msg_type = "voice"
        elif update.callback_query:
            msg_type = "callback_query"

        TELEGRAM_MESSAGES_RECEIVED_TOTAL.labels(type=msg_type).inc()

        if not update.effective_user or not settings.ALLOWED_TELEGRAM_USERNAMES:
            return

        allowed_users = [
            u.strip().lower() for u in settings.ALLOWED_TELEGRAM_USERNAMES.split(",") if u.strip()
        ]
        username = update.effective_user.username

        if not username or username.lower() not in allowed_users:
            TELEGRAM_MESSAGES_RECEIVED_TOTAL.labels(type="unauthorized").inc()
            if update.message:
                await update.message.reply_text(
                    "Acesso Negado: Você não tem permissão para usar este bot."
                )
            raise ApplicationHandlerStop()

    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Register auth middleware
    application.add_handler(TypeHandler(Update, auth_middleware), group=-1)

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Register conversation handlers
    application.add_handler(expense_conv_handler)
    for handler in balance_handlers:
        application.add_handler(handler)

    # Register photo handler (before text handler to prioritize photos)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))

    # Register voice/audio handler
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message))

    # Register text message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Register agent callback handler
    application.add_handler(agent_callback_handler)

    logger.info("Handlers registered successfully")

    # Handle graceful shutdown and startup
    async def post_init(application):
        """Initialize resources on startup."""
        logger.info("Initializing resources...")
        await init_db()

        # Schedule weekly balance summary (Friday 10:00 AM)
        # Note: timezone is UTC by default in APScheduler/JobQueue, adjust to UTC-3 (Brazil)
        # 10:00 AM BRT is 13:00 UTC
        utc_time = datetime.time(hour=13, minute=0, second=0)
        application.job_queue.run_daily(
            send_weekly_balance_summary,
            time=utc_time,
            days=(4,),  # 4 = Friday in python-telegram-bot run_daily (0=Mon, 6=Sun)
        )
        logger.info("Scheduled weekly balance summary for Friday 10:00 AM (BRT)")

    async def shutdown(application):
        """Cleanup on shutdown."""
        logger.info("Shutting down, cleaning up resources...")
        await close_http_client()
        await close_db()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the bot (polling mode)
    logger.info(
        f"Bot started. Polling Telegram for updates and forwarding to agent_api: {settings.AGENT_API_URL}"
    )

    # Register startup and shutdown handlers with application
    application.post_init = post_init
    application.post_shutdown = shutdown

    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def send_weekly_balance_summary(context) -> None:
    """Send weekly balance summary to all allowed users."""
    logger.info("Running weekly balance summary job")

    # Get all allowed users
    if not settings.ALLOWED_TELEGRAM_USERNAMES:
        return

    allowed_users = [
        u.strip().lower() for u in settings.ALLOWED_TELEGRAM_USERNAMES.split(",") if u.strip()
    ]

    if not allowed_users:
        return

    try:
        img_data = await get_balance_graph(categories=None, mode="saldo")
        if not img_data:
            logger.info("No balance graph available for weekly summary.")
            return

        caption = "Aqui está seu *Resumo Semanal de Saldos e Limites*!"

        async with get_db() as session:
            # Select distinct chat_ids from sessions table (if they ever interacted)
            result = await session.execute(text("SELECT DISTINCT chat_id FROM chat_sessions"))
            chat_ids = [row[0] for row in result.fetchall()]

            for chat_id in chat_ids:
                try:
                    await context.bot.send_photo(
                        chat_id=chat_id, photo=img_data, caption=caption, parse_mode="Markdown"
                    )
                    logger.info(f"Sent weekly summary graph to chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to send weekly summary graph to {chat_id}: {e}")

    except Exception as e:
        logger.error(f"Error generating weekly balance summary graph: {e}")


if __name__ == "__main__":
    main()
