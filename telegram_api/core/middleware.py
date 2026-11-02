"""Authorization middleware applied to every incoming Telegram update."""

from telegram import Message, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from telegram_api.core.metrics import TELEGRAM_MESSAGES_RECEIVED_TOTAL
from telegram_api.settings import settings

DENIED_MESSAGE = "Acesso Negado: Você não tem permissão para usar este bot."


def _detect_media_type(message: Message) -> str:
    if message.photo:
        return "photo"
    if message.voice or message.audio:
        return "voice"
    return "unknown"


def _detect_message_type(update: Update) -> str:
    message = update.message
    if message:
        if message.text:
            return "command" if message.text.startswith("/") else "text"
        return _detect_media_type(message)
    return "callback_query" if update.callback_query else "unknown"


def _allowed_usernames() -> list[str]:
    raw = settings.ALLOWED_TELEGRAM_USERNAMES
    return [username.strip().lower() for username in raw.split(",") if username.strip()]


def _is_authorized(update: Update, allowed_usernames: list[str]) -> bool:
    user = update.effective_user
    if not user or not user.username:
        return False
    return user.username.lower() in allowed_usernames


async def _deny_access(update: Update) -> None:
    TELEGRAM_MESSAGES_RECEIVED_TOTAL.labels(type="unauthorized").inc()
    if update.message:
        await update.message.reply_text(DENIED_MESSAGE)
    raise ApplicationHandlerStop()


async def auth_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Record received-message metrics and block users outside the allow-list."""
    TELEGRAM_MESSAGES_RECEIVED_TOTAL.labels(type=_detect_message_type(update)).inc()

    if not update.effective_user or not settings.ALLOWED_TELEGRAM_USERNAMES:
        return

    if not _is_authorized(update, _allowed_usernames()):
        await _deny_access(update)
