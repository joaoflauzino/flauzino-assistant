"""Pure Markdown-to-Telegram-HTML formatting and keyboard building."""

import html
import re
from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


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


def format_code_block(match: re.Match[str]) -> str:
    """Renders a fenced code block match as Telegram ``<pre>`` markup."""
    language = (match.group(1) or "").strip()
    code = html.escape(match.group(2), quote=False)
    if language:
        return f'<pre><code class="language-{language}">{code}</code></pre>'
    return f"<pre>{code}</pre>"


def format_inline_code(match: re.Match[str]) -> str:
    """Renders an inline code match as Telegram ``<code>`` markup."""
    return f"<code>{html.escape(match.group(1), quote=False)}</code>"


def protect_code(text: str) -> tuple[str, list[str], list[str]]:
    """Replaces code spans with placeholders so later rules cannot touch them."""
    code_blocks: list[str] = []
    inline_codes: list[str] = []

    def save_code_block(match: re.Match[str]) -> str:
        code_blocks.append(format_code_block(match))
        return f"\x00CODEBLOCK{len(code_blocks) - 1}\x00"

    def save_inline_code(match: re.Match[str]) -> str:
        inline_codes.append(format_inline_code(match))
        return f"\x00INLINECODE{len(inline_codes) - 1}\x00"

    protected = _CODE_BLOCK_PATTERN.sub(save_code_block, text)
    protected = _INLINE_CODE_PATTERN.sub(save_inline_code, protected)
    protected = html.escape(protected, quote=False)
    return protected, code_blocks, inline_codes


def apply_markdown_rules(text: str) -> str:
    """Applies every Markdown rule to already escaped text."""
    for rule in MARKDOWN_RULES:
        text = re.sub(rule.pattern, rule.replacement, text, flags=rule.flags)
    return text


def restore_code(text: str, code_blocks: list[str], inline_codes: list[str]) -> str:
    """Puts the previously protected code spans back in place."""
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

    protected, code_blocks, inline_codes = protect_code(text)
    rendered = apply_markdown_rules(protected)
    return restore_code(rendered, code_blocks, inline_codes)


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
