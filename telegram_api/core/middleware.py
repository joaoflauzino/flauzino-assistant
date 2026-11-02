"""Authorization middleware applied to every incoming Telegram update."""

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from telegram_api.core.metrics import TELEGRAM_MESSAGES_RECEIVED_TOTAL
from telegram_api.core.utils import detect_message_type
from telegram_api.settings import settings

DENIED_MESSAGE = "Acesso Negado: Você não tem permissão para usar este bot."


def allowed_usernames() -> list[str]:
    """Parses the allow-list of Telegram usernames from the settings."""
    raw = settings.ALLOWED_TELEGRAM_USERNAMES
    return [username.strip().lower() for username in raw.split(",") if username.strip()]


def is_authorized(update: Update, usernames: list[str]) -> bool:
    """Tells whether the update's author is in the allow-list."""
    user = update.effective_user
    if not user or not user.username:
        return False
    return user.username.lower() in usernames


async def deny_access(update: Update) -> None:
    """Counts the unauthorized message, warns the user and stops the handler chain."""
    TELEGRAM_MESSAGES_RECEIVED_TOTAL.labels(type="unauthorized").inc()
    if update.message:
        await update.message.reply_text(DENIED_MESSAGE)
    raise ApplicationHandlerStop()


async def auth_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Record received-message metrics and block users outside the allow-list."""
    TELEGRAM_MESSAGES_RECEIVED_TOTAL.labels(type=detect_message_type(update)).inc()

    if not update.effective_user or not settings.ALLOWED_TELEGRAM_USERNAMES:
        return

    if not is_authorized(update, allowed_usernames()):
        await deny_access(update)
