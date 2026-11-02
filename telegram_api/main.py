"""Main entry point for the Telegram bot."""

import datetime
import signal
import sys
from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from telegram_api.core.database import close_db, init_db
from telegram_api.core.finance_client import get_balance_graph
from telegram_api.core.http_client import close_http_client
from telegram_api.core.logger import get_logger
from telegram_api.core.metrics import start_metrics_server
from telegram_api.core.middleware import auth_middleware
from telegram_api.handlers.balance_handler import balance_handlers
from telegram_api.handlers.balance_summary_handler import balanco_handler
from telegram_api.handlers.command_handler import help_command, start_command
from telegram_api.handlers.expense_handler import expense_conv_handler
from telegram_api.handlers.income_handler import income_conv_handler
from telegram_api.handlers.message_handler import agent_callback_handler, handle_text_message
from telegram_api.handlers.photo_handler import handle_photo_message
from telegram_api.handlers.voice_handler import handle_voice_message
from telegram_api.services.session_service import SessionService
from telegram_api.settings import settings

logger = get_logger(__name__)

WEEKLY_SUMMARY_UTC_TIME = datetime.time(hour=13, minute=0, second=0)
WEEKLY_SUMMARY_DAYS = (4,)  # 4 = Friday in python-telegram-bot run_daily (0=Mon, 6=Sun)
WEEKLY_SUMMARY_CAPTION = "Aqui está seu *Resumo Semanal de Saldos e Limites*!"


def register_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(balanco_handler)

    application.add_handler(expense_conv_handler)
    application.add_handler(income_conv_handler)
    for handler in balance_handlers:
        application.add_handler(handler)

    # Photo must be registered before text so photos are not handled as text.
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(agent_callback_handler)


def schedule_weekly_summary(application: Application) -> None:
    # Note: APScheduler/JobQueue runs in UTC by default; 10:00 BRT is 13:00 UTC.
    job_queue = application.job_queue
    if job_queue is None:
        logger.warning("Job queue unavailable; weekly balance summary was not scheduled.")
        return
    job_queue.run_daily(
        send_weekly_balance_summary,
        time=WEEKLY_SUMMARY_UTC_TIME,
        days=WEEKLY_SUMMARY_DAYS,
    )


async def post_init(application: Application) -> None:
    logger.info("Initializing resources...")
    await init_db()
    schedule_weekly_summary(application)
    logger.info("Scheduled weekly balance summary for Friday 10:00 AM (BRT)")


async def post_shutdown(application: Application) -> None:
    logger.info("Shutting down, cleaning up resources...")
    await close_http_client()
    await close_db()


def signal_handler(signum: int, frame: Any) -> None:
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def register_signal_handlers() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def build_application() -> Application:
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(TypeHandler(Update, auth_middleware), group=-1)
    register_handlers(application)
    application.post_init = post_init
    application.post_shutdown = post_shutdown
    return application


def main() -> None:
    """Start the Telegram bot."""
    logger.info("Starting Telegram bot...")

    start_metrics_server(port=settings.METRICS_PORT)
    logger.info(f"Prometheus metrics server started on port {settings.METRICS_PORT}")

    application = build_application()
    logger.info("Handlers registered successfully")

    register_signal_handlers()
    logger.info(
        f"Bot started. Polling Telegram for updates and forwarding to agent_api: {settings.AGENT_API_URL}"
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def send_summary_photos(
    context: ContextTypes.DEFAULT_TYPE, chat_ids: list[int], img_data: bytes
) -> None:
    for chat_id in chat_ids:
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=img_data,
                caption=WEEKLY_SUMMARY_CAPTION,
                parse_mode="Markdown",
            )
            logger.info(f"Sent weekly summary graph to chat {chat_id}")
        except Exception as e:  # Boundary: one failing chat must not stop the others.
            logger.error(f"Failed to send weekly summary graph to {chat_id}: {e}")


async def send_weekly_balance_summary(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send weekly balance summary to all allowed users."""
    logger.info("Running weekly balance summary job")

    if not settings.ALLOWED_TELEGRAM_USERNAMES:
        return

    try:
        img_data = await get_balance_graph(categories=None, mode="saldo")
        if not img_data:
            logger.info("No balance graph available for weekly summary.")
            return

        chat_ids = await SessionService().list_known_chat_ids()
        await send_summary_photos(context, chat_ids, img_data)
    except Exception as e:  # Boundary: job failures are logged, never raised to the scheduler.
        logger.error(f"Error generating weekly balance summary graph: {e}")


if __name__ == "__main__":
    main()
