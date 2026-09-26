import pytest
from unittest.mock import AsyncMock
from telegram.error import BadRequest
from telegram.constants import ParseMode

from telegram_api.core.formatter import markdown_to_telegram_html, send_agent_reply


def test_markdown_to_telegram_html_empty_or_none():
    assert markdown_to_telegram_html(None) == ""
    assert markdown_to_telegram_html("") == ""


def test_markdown_to_telegram_html_user_case():
    text = (
        "✅ Gasto registrado com sucesso!\n\n"
        "- **Categoria:** alimentação\n"
        "- **Valor:** **R$ 80,00**\n"
        "- **Item:** carne\n"
        "- **Pagamento:** c6_joao\n"
        "- **Local:** BH"
    )
    result = markdown_to_telegram_html(text)

    # Asserts bold tags
    assert "<b>Categoria:</b>" in result
    assert "<b>Valor:</b>" in result
    assert "<b>R$ 80,00</b>" in result
    assert "<b>Item:</b>" in result
    assert "<b>Pagamento:</b>" in result
    assert "<b>Local:</b>" in result

    # Asserts snake_case is preserved and NOT treated as italic
    assert "c6_joao" in result
    assert "<i>joao</i>" not in result
    assert "c6<i>joao</i>" not in result


def test_markdown_to_telegram_html_formatting():
    # Headers
    assert markdown_to_telegram_html("# Título Principal") == "<b>Título Principal</b>"
    assert markdown_to_telegram_html("## Subtítulo") == "<b>Subtítulo</b>"

    # Bold & Italic combined
    assert markdown_to_telegram_html("***Muito Importante***") == "<b><i>Muito Importante</i></b>"

    # Bold with double underscore
    assert markdown_to_telegram_html("__Texto em Negrito__") == "<b>Texto em Negrito</b>"

    # Italic with single asterisk and single underscore
    assert markdown_to_telegram_html("*Texto em itálico*") == "<i>Texto em itálico</i>"
    assert markdown_to_telegram_html("Veja _isso aqui_ agora") == "Veja <i>isso aqui</i> agora"

    # Strikethrough
    assert markdown_to_telegram_html("~~Cancelado~~") == "<s>Cancelado</s>"

    # Links
    assert (
        markdown_to_telegram_html("[Google](https://google.com)")
        == '<a href="https://google.com">Google</a>'
    )


def test_markdown_to_telegram_html_preserves_code():
    # Inline code
    code_text = "Execute `/gasto` ou `cat file.txt`."
    res = markdown_to_telegram_html(code_text)
    assert "<code>/gasto</code>" in res
    assert "<code>cat file.txt</code>" in res

    # Code block with language and special characters
    code_block = (
        "Aqui está o código:\n" "```python\n" "if a < b and c > d:\n" "    return a & b\n" "```"
    )
    res = markdown_to_telegram_html(code_block)
    assert '<pre><code class="language-python">' in res
    assert "if a &lt; b and c &gt; d:\n    return a &amp; b" in res
    assert "</code></pre>" in res


def test_markdown_to_telegram_html_escapes_unsafe_html():
    raw_html = "Total < 100 & saldo > 50 <script>alert(1)</script>"
    res = markdown_to_telegram_html(raw_html)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in res
    assert "&lt; 100" in res
    assert "&amp;" in res
    assert "&gt; 50" in res


def test_markdown_to_telegram_html_snake_case_not_italicized():
    text = "IDs: user_id_123 e conta_bancaria_c6 e c6_joao_master."
    res = markdown_to_telegram_html(text)
    assert "user_id_123" in res
    assert "conta_bancaria_c6" in res
    assert "c6_joao_master" in res
    assert "<i>" not in res


@pytest.mark.asyncio
async def test_send_agent_reply_text_success():
    msg = AsyncMock()
    msg.reply_text = AsyncMock()

    await send_agent_reply(msg, "Olá **mundo**!")

    msg.reply_text.assert_called_once()
    args, kwargs = msg.reply_text.call_args
    assert args[0] == "Olá <b>mundo</b>!"
    assert kwargs.get("parse_mode") == ParseMode.HTML


@pytest.mark.asyncio
async def test_send_agent_reply_text_fallback_on_parse_error():
    msg = AsyncMock()
    # First call with HTML raises parse error, second call (fallback) succeeds
    msg.reply_text = AsyncMock(
        side_effect=[
            BadRequest("Can't parse entities: can't find end of the entity"),
            AsyncMock(),
        ]
    )

    await send_agent_reply(msg, "Texto com erro **não fechado")

    assert msg.reply_text.call_count == 2
    # Second call should be plain text without parse_mode
    second_call_args = msg.reply_text.call_args_list[1][0]
    second_call_kwargs = msg.reply_text.call_args_list[1][1]
    assert second_call_args[0] == "Texto com erro **não fechado"
    assert "parse_mode" not in second_call_kwargs


@pytest.mark.asyncio
async def test_send_agent_reply_photo_success():
    msg = AsyncMock()
    msg.reply_photo = AsyncMock()

    # Valid base64 1x1 png or simple dummy
    dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    await send_agent_reply(msg, "Gráfico **semanal**", image_base64=dummy_b64)

    msg.reply_photo.assert_called_once()
    args, kwargs = msg.reply_photo.call_args
    assert kwargs.get("caption") == "Gráfico <b>semanal</b>"
    assert kwargs.get("parse_mode") == ParseMode.HTML
    assert kwargs.get("photo") is not None


@pytest.mark.asyncio
async def test_send_agent_reply_photo_fallback_on_parse_error():
    msg = AsyncMock()
    msg.reply_photo = AsyncMock(
        side_effect=[
            BadRequest("Can't parse entities: error"),
            AsyncMock(),
        ]
    )
    dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    await send_agent_reply(msg, "Legenda com erro", image_base64=dummy_b64)

    assert msg.reply_photo.call_count == 2
    second_call_kwargs = msg.reply_photo.call_args_list[1][1]
    assert second_call_kwargs.get("caption") == "Legenda com erro"
    assert "parse_mode" not in second_call_kwargs
