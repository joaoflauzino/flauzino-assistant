"""Main entry point for the Telegram bot."""

import signal
import sys
import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    ApplicationHandlerStop,
    filters,
)

from telegram_api.settings import settings
from telegram_api.core.logger import get_logger
from telegram_api.core.http_client import close_http_client
from telegram_api.core.database import init_db, close_db
from telegram_api.handlers.command_handler import start_command, help_command
from telegram_api.handlers.message_handler import handle_text_message, agent_callback_handler
from telegram_api.handlers.photo_handler import handle_photo_message
from telegram_api.handlers.voice_handler import handle_voice_message
from telegram_api.handlers.expense_handler import expense_conv_handler
from telegram_api.handlers.balance_handler import balance_handlers

logger = get_logger(__name__)


def main() -> None:
    """Start the Telegram bot."""
    logger.info("Starting Telegram bot...")

    async def auth_middleware(update: Update, context) -> None:
        """Middleware to check if the user is allowed to use the bot."""
        if not update.effective_user or not settings.ALLOWED_TELEGRAM_USERNAMES:
            return

        allowed_users = [
            u.strip().lower() for u in settings.ALLOWED_TELEGRAM_USERNAMES.split(",") if u.strip()
        ]
        username = update.effective_user.username

        if not username or username.lower() not in allowed_users:
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
    import httpx

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
        import base64

        async with httpx.AsyncClient() as client:
            fin_url = f"{settings.FINANCE_SERVICE_URL}/limits/balance"
            fin_resp = await client.get(fin_url)
            fin_resp.raise_for_status()
            balances = fin_resp.json()

            if not balances:
                logger.info("No balance data available for weekly summary.")
                return

            graph_url = f"{settings.GRAPH_SERVICE_URL}/graphs/bar"
            response = await client.post(graph_url, json={"balances": balances, "mode": "saldo"})
            response.raise_for_status()

            data = response.json()
            if "image_base64" not in data:
                logger.error("No image returned from graph_api for weekly summary.")
                return

            img_data = base64.b64decode(data["image_base64"])
            caption = "Aqui está seu *Resumo Semanal de Saldos e Limites*!"

            from telegram_api.core.database import get_db
            from sqlalchemy import text

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
