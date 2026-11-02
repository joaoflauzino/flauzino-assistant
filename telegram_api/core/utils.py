"""Pure helpers shared by the Telegram bot core."""

from telegram import Message, Update


def detect_media_type(message: Message) -> str:
    """Classifies a message with media as photo, voice or unknown."""
    if message.photo:
        return "photo"
    if message.voice or message.audio:
        return "voice"
    return "unknown"


def detect_message_type(update: Update) -> str:
    """Classifies an update for metrics: command, text, photo, voice, callback or unknown."""
    message = update.message
    if message:
        if message.text:
            return "command" if message.text.startswith("/") else "text"
        return detect_media_type(message)
    return "callback_query" if update.callback_query else "unknown"


def format_currency(value: float) -> str:
    """Formats a signed amount as ``+R$ 1.234,56`` / ``-R$ 1.234,56`` / ``R$ 0,00``."""
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "+" if value > 0 else ("-" if value < 0 else "")
    return f"{sign}R$ {formatted}"
