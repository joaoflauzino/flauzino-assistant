"""Telegram message delivery: HTML fallback, text replies and photo replies."""

import base64
import io
from collections.abc import Awaitable, Callable
from typing import Any

from telegram import InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest

from telegram_api.core.formatter import markdown_to_telegram_html
from telegram_api.core.logger import get_logger

logger = get_logger(__name__)


def is_parse_error(exc: BadRequest) -> bool:
    """Tells whether a Telegram BadRequest was caused by HTML entity parsing."""
    message = str(exc).lower()
    return "parse" in message or "entities" in message


def markup_payload(
    reply_markup: InlineKeyboardMarkup | None, parse_mode: str | None
) -> dict[str, Any]:
    """Builds the optional ``parse_mode``/``reply_markup`` kwargs for a send call."""
    payload: dict[str, Any] = {}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return payload


def photo_payload(
    image_data: bytes,
    caption: str,
    parse_mode: str | None,
    reply_markup: InlineKeyboardMarkup | None,
) -> dict[str, Any]:
    """Builds the kwargs for a ``reply_photo`` call."""
    return {
        "photo": io.BytesIO(image_data),
        "caption": caption,
        **markup_payload(reply_markup, parse_mode),
    }


async def send_with_html_fallback(
    send_html: Callable[[], Awaitable[Any]],
    send_plain: Callable[[], Awaitable[Any]],
    channel: str,
) -> None:
    """Runs the HTML send and retries as plain text when Telegram rejects the markup."""
    try:
        await send_html()
        return
    except BadRequest as exc:
        if not is_parse_error(exc):
            raise
        logger.warning(
            f"Telegram HTML parsing failed for {channel}, falling back to plain text: {exc}"
        )
    await send_plain()


async def send_photo(
    target_message: Any,
    image_data: bytes,
    formatted_text: str,
    plain_text: str,
    reply_markup: InlineKeyboardMarkup | None,
) -> None:
    """Replies with a photo, falling back to a plain caption when the HTML caption fails."""
    await send_with_html_fallback(
        lambda: target_message.reply_photo(
            **photo_payload(image_data, formatted_text, ParseMode.HTML, reply_markup)
        ),
        lambda: target_message.reply_photo(
            **photo_payload(image_data, plain_text, None, reply_markup)
        ),
        "photo caption",
    )


async def send_text(
    target_message: Any,
    formatted_text: str,
    plain_text: str,
    reply_markup: InlineKeyboardMarkup | None,
) -> None:
    """Replies with text, falling back to plain text when the HTML markup fails."""
    await send_with_html_fallback(
        lambda: target_message.reply_text(
            formatted_text, **markup_payload(reply_markup, ParseMode.HTML)
        ),
        lambda: target_message.reply_text(plain_text, **markup_payload(reply_markup, None)),
        "text message",
    )


async def send_agent_reply(
    target_message: Any,
    text: str,
    image_base64: str | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Send formatted response to Telegram with automatic HTML formatting and fallback.

    Args:
        target_message: Telegram Message object (e.g. update.message or query.message).
        text: Response message in Markdown.
        image_base64: Optional base64-encoded image to reply with.
        reply_markup: Optional inline keyboard markup.
    """
    formatted_text = markdown_to_telegram_html(text)

    if image_base64:
        await send_photo(
            target_message, base64.b64decode(image_base64), formatted_text, text, reply_markup
        )
        return

    await send_text(target_message, formatted_text, text, reply_markup)
