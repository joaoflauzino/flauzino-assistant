"""Telegram message formatting and delivery helpers."""

import base64
import html
import io
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest

from telegram_api.core.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class MarkdownRule:
    """A single Markdown-to-HTML rewrite applied in declaration order."""

    pattern: str
    replacement: str
    flags: int = 0


MARKDOWN_RULES: tuple[MarkdownRule, ...] = (
    MarkdownRule(r"^(#{1,6})\s+(.+)$", r"<b>\2</b>", re.MULTILINE),
    MarkdownRule(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", re.DOTALL),
    MarkdownRule(r"\*\*(.+?)\*\*", r"<b>\1</b>", re.DOTALL),
    MarkdownRule(r"(?<![a-zA-Z0-9])__(.+?)__(?![a-zA-Z0-9])", r"<b>\1</b>", re.DOTALL),
    MarkdownRule(r"(?<!\*)\*(?!\s)([^\*\n]+?)(?<!\s)\*(?!\*)", r"<i>\1</i>"),
    MarkdownRule(
        r"(?<![a-zA-Z0-9])_([^_ \n][^_]*?[^_ \n]|[a-zA-Z0-9])_(?![a-zA-Z0-9])",
        r"<i>\1</i>",
    ),
    MarkdownRule(r"~~(.+?)~~", r"<s>\1</s>"),
    MarkdownRule(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)", r'<a href="\2">\1</a>'),
)

_CODE_BLOCK_PATTERN = re.compile(r"```([a-zA-Z0-9_-]*)\n?(.*?)\n?```", re.DOTALL)
_INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")


def _format_code_block(match: re.Match[str]) -> str:
    language = (match.group(1) or "").strip()
    code = html.escape(match.group(2), quote=False)
    if language:
        return f'<pre><code class="language-{language}">{code}</code></pre>'
    return f"<pre>{code}</pre>"


def _format_inline_code(match: re.Match[str]) -> str:
    return f"<code>{html.escape(match.group(1), quote=False)}</code>"


def _protect_code(text: str) -> tuple[str, list[str], list[str]]:
    """Replace code spans with placeholders so later rules cannot touch them."""
    code_blocks: list[str] = []
    inline_codes: list[str] = []

    def save_code_block(match: re.Match[str]) -> str:
        code_blocks.append(_format_code_block(match))
        return f"\x00CODEBLOCK{len(code_blocks) - 1}\x00"

    def save_inline_code(match: re.Match[str]) -> str:
        inline_codes.append(_format_inline_code(match))
        return f"\x00INLINECODE{len(inline_codes) - 1}\x00"

    protected = _CODE_BLOCK_PATTERN.sub(save_code_block, text)
    protected = _INLINE_CODE_PATTERN.sub(save_inline_code, protected)
    protected = html.escape(protected, quote=False)
    return protected, code_blocks, inline_codes


def _apply_markdown_rules(text: str) -> str:
    for rule in MARKDOWN_RULES:
        text = re.sub(rule.pattern, rule.replacement, text, flags=rule.flags)
    return text


def _restore_code(text: str, code_blocks: list[str], inline_codes: list[str]) -> str:
    for index, tag in enumerate(inline_codes):
        text = text.replace(f"\x00INLINECODE{index}\x00", tag)
    for index, tag in enumerate(code_blocks):
        text = text.replace(f"\x00CODEBLOCK{index}\x00", tag)
    return text


def markdown_to_telegram_html(text: str | None) -> str:
    """Convert common Markdown (CommonMark / GFM) to Telegram-supported HTML.

    Preserves code blocks and inline code, escapes raw HTML entities in regular text,
    and safely converts Markdown formatting (headers, bold, italic, strikethrough, links)
    without breaking snake_case identifiers (e.g., c6_joao).
    """
    if not text:
        return ""

    protected, code_blocks, inline_codes = _protect_code(text)
    rendered = _apply_markdown_rules(protected)
    return _restore_code(rendered, code_blocks, inline_codes)


def _is_parse_error(exc: BadRequest) -> bool:
    message = str(exc).lower()
    return "parse" in message or "entities" in message


def _markup_payload(
    reply_markup: InlineKeyboardMarkup | None, parse_mode: str | None
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return payload


def _photo_payload(
    image_data: bytes,
    caption: str,
    parse_mode: str | None,
    reply_markup: InlineKeyboardMarkup | None,
) -> dict[str, Any]:
    return {
        "photo": io.BytesIO(image_data),
        "caption": caption,
        **_markup_payload(reply_markup, parse_mode),
    }


async def _send_with_html_fallback(
    send_html: Callable[[], Awaitable[Any]],
    send_plain: Callable[[], Awaitable[Any]],
    channel: str,
) -> None:
    try:
        await send_html()
        return
    except BadRequest as exc:
        if not _is_parse_error(exc):
            raise
        logger.warning(
            f"Telegram HTML parsing failed for {channel}, falling back to plain text: {exc}"
        )
    await send_plain()


async def _send_photo(
    target_message: Any,
    image_data: bytes,
    formatted_text: str,
    plain_text: str,
    reply_markup: InlineKeyboardMarkup | None,
) -> None:
    await _send_with_html_fallback(
        lambda: target_message.reply_photo(
            **_photo_payload(image_data, formatted_text, ParseMode.HTML, reply_markup)
        ),
        lambda: target_message.reply_photo(
            **_photo_payload(image_data, plain_text, None, reply_markup)
        ),
        "photo caption",
    )


async def _send_text(
    target_message: Any,
    formatted_text: str,
    plain_text: str,
    reply_markup: InlineKeyboardMarkup | None,
) -> None:
    await _send_with_html_fallback(
        lambda: target_message.reply_text(
            formatted_text, **_markup_payload(reply_markup, ParseMode.HTML)
        ),
        lambda: target_message.reply_text(plain_text, **_markup_payload(reply_markup, None)),
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
        await _send_photo(
            target_message, base64.b64decode(image_base64), formatted_text, text, reply_markup
        )
        return

    await _send_text(target_message, formatted_text, text, reply_markup)


def build_options_keyboard(
    options: list[str] | None, prefix: str = "agent_opt:", columns: int = 2
) -> InlineKeyboardMarkup | None:
    """Build an InlineKeyboardMarkup with action buttons from a list of option strings.

    Args:
        options: List of string options to display as buttons.
        prefix: Callback data prefix for the options.
        columns: Maximum number of buttons per row (default: 2).

    Returns:
        InlineKeyboardMarkup or None if options is empty or invalid.
    """
    if not options or not isinstance(options, list):
        return None

    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for option in options:
        row.append(InlineKeyboardButton(option, callback_data=f"{prefix}{option}"))
        if len(row) == columns:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard) if keyboard else None
