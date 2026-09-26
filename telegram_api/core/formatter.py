"""Telegram message formatting and delivery helpers."""

import base64
import html
import io
import re
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest

from telegram_api.core.logger import get_logger

logger = get_logger(__name__)


def markdown_to_telegram_html(text: str | None) -> str:
    """Convert common Markdown (CommonMark / GFM) to Telegram-supported HTML.

    Preserves code blocks and inline code, escapes raw HTML entities in regular text,
    and safely converts Markdown formatting (headers, bold, italic, strikethrough, links)
    without breaking snake_case identifiers (e.g., c6_joao).
    """
    if not text:
        return ""

    code_blocks: list[str] = []
    inline_codes: list[str] = []

    # 1. Extract fenced code blocks: ```lang\ncode\n```
    def save_code_block(match: re.Match) -> str:
        lang = (match.group(1) or "").strip()
        code = match.group(2)
        escaped_code = html.escape(code, quote=False)
        idx = len(code_blocks)
        if lang:
            tag = f'<pre><code class="language-{lang}">{escaped_code}</code></pre>'
        else:
            tag = f"<pre>{escaped_code}</pre>"
        code_blocks.append(tag)
        return f"\x00CODEBLOCK{idx}\x00"

    processed = re.sub(r"```([a-zA-Z0-9_-]*)\n?(.*?)\n?```", save_code_block, text, flags=re.DOTALL)

    # 2. Extract inline code `code`
    def save_inline_code(match: re.Match) -> str:
        code = match.group(1)
        escaped_code = html.escape(code, quote=False)
        idx = len(inline_codes)
        inline_codes.append(f"<code>{escaped_code}</code>")
        return f"\x00INLINECODE{idx}\x00"

    processed = re.sub(r"`([^`]+)`", save_inline_code, processed)

    # 3. Escape HTML characters (&, <, >) in remaining regular text
    processed = html.escape(processed, quote=False)

    # 4. Headers (# Title -> <b>Title</b>)
    processed = re.sub(r"^(#{1,6})\s+(.+)$", r"<b>\2</b>", processed, flags=re.MULTILINE)

    # 5. Bold + Italic combined: ***text*** -> <b><i>text</i></b>
    processed = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", processed, flags=re.DOTALL)

    # 6. Bold: **text** or __text__
    processed = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", processed, flags=re.DOTALL)
    processed = re.sub(
        r"(?<![a-zA-Z0-9])__(.+?)__(?![a-zA-Z0-9])", r"<b>\1</b>", processed, flags=re.DOTALL
    )

    # 7. Italic: *text* or _text_
    # Single asterisk: must not be adjacent to another asterisk, and must not have whitespace around borders
    processed = re.sub(r"(?<!\*)\*(?!\s)([^\*\n]+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", processed)
    # Single underscore: only at word boundaries (preserves snake_case like c6_joao)
    processed = re.sub(
        r"(?<![a-zA-Z0-9])_([^_ \n][^_]*?[^_ \n]|[a-zA-Z0-9])_(?![a-zA-Z0-9])",
        r"<i>\1</i>",
        processed,
    )

    # 8. Strikethrough: ~~text~~ -> <s>text</s>
    processed = re.sub(r"~~(.+?)~~", r"<s>\1</s>", processed)

    # 9. Links: [text](url) -> <a href="url">text</a>
    processed = re.sub(r"\[([^\]]+)\]\((https?://[^\s\)]+)\)", r'<a href="\2">\1</a>', processed)

    # 10. Restore code blocks and inline code
    for i, tag in enumerate(inline_codes):
        processed = processed.replace(f"\x00INLINECODE{i}\x00", tag)
    for i, tag in enumerate(code_blocks):
        processed = processed.replace(f"\x00CODEBLOCK{i}\x00", tag)

    return processed


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
        image_data = base64.b64decode(image_base64)
        try:
            kwargs: dict[str, Any] = {
                "photo": io.BytesIO(image_data),
                "caption": formatted_text,
                "parse_mode": ParseMode.HTML,
            }
            if reply_markup:
                kwargs["reply_markup"] = reply_markup
            await target_message.reply_photo(**kwargs)
        except BadRequest as e:
            if "parse" in str(e).lower() or "entities" in str(e).lower():
                logger.warning(
                    f"Telegram HTML parsing failed for photo caption, falling back to plain text: {e}"
                )
                kwargs = {
                    "photo": io.BytesIO(image_data),
                    "caption": text,
                }
                if reply_markup:
                    kwargs["reply_markup"] = reply_markup
                await target_message.reply_photo(**kwargs)
            else:
                raise
    else:
        try:
            kwargs = {
                "parse_mode": ParseMode.HTML,
            }
            if reply_markup:
                kwargs["reply_markup"] = reply_markup
            await target_message.reply_text(formatted_text, **kwargs)
        except BadRequest as e:
            if "parse" in str(e).lower() or "entities" in str(e).lower():
                logger.warning(
                    f"Telegram HTML parsing failed for text message, falling back to plain text: {e}"
                )
                kwargs = {}
                if reply_markup:
                    kwargs["reply_markup"] = reply_markup
                await target_message.reply_text(text, **kwargs)
            else:
                raise


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
