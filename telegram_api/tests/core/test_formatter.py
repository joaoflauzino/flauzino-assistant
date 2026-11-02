from telegram_api.core.formatter import build_options_keyboard, markdown_to_telegram_html


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
    code_block = "Aqui está o código:\n```python\nif a < b and c > d:\n    return a & b\n```"
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


def test_build_options_keyboard():
    # Empty or None cases
    assert build_options_keyboard(None) is None
    assert build_options_keyboard([]) is None

    # Normal options with default 2 columns
    options = ["Opção 1", "Opção 2", "Opção 3"]
    markup = build_options_keyboard(options)
    assert markup is not None
    assert len(markup.inline_keyboard) == 2
    assert len(markup.inline_keyboard[0]) == 2
    assert len(markup.inline_keyboard[1]) == 1

    btn1 = markup.inline_keyboard[0][0]
    assert btn1.text == "Opção 1"
    assert btn1.callback_data == "agent_opt:Opção 1"

    # Custom prefix and columns
    markup_custom = build_options_keyboard(options, prefix="custom:", columns=3)
    assert markup_custom is not None
    assert len(markup_custom.inline_keyboard) == 1
    assert len(markup_custom.inline_keyboard[0]) == 3
    assert markup_custom.inline_keyboard[0][0].callback_data == "custom:Opção 1"
