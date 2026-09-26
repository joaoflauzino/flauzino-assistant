# Walkthrough: Correção de Parsing Markdown e Formatação HTML no Telegram Bot

Este documento resume a resolução do erro de parsing de Markdown no `telegram_api` e a implementação do novo formatador HTML para o Telegram.

---

## 1. Problema Identificado

Nos logs do `telegram_api`, ocorria a falha:
```text
[WARNING] [telegram_api.handlers.message_handler] Markdown parsing failed: Can't parse entities: can't find end of the entity starting at byte offset 136
```

### Causa Raiz:
- O bot utilizava `ParseMode.MARKDOWN` (versão 1 legada do Telegram).
- O agente LLM (Gemini) respondia em Markdown padrão (CommonMark / GFM):
  - Negrito com duplo asterisco: `**Categoria:**`, `**Valor:** **R$ 80,00**`.
  - Snake_case: `c6_joao`.
- No Markdown v1 do Telegram:
  - Underscores não pareados (como em `c6_joao`) abriam entidades itálicas que nunca fechavam, gerando erro 400 (`BadRequest`).
  - Negrito com `**` causava confusão de contagem de entidades.
- O fallback para texto puro fazia o bot exibir os caracteres literais `**`, `_` e `-` sem formatação no chat.

---

## 2. Alterações Realizadas

### 2.1. Novo Módulo de Formatação ([telegram_api/core/formatter.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/core/formatter.py))
- **`markdown_to_telegram_html(text: str | None) -> str`**:
  - Extrai blocos de código com linguagem opcional (```` ```python ... ``` ````) e código inline (`` `...` ``), preservando a integridade interna.
  - Escapa caracteres HTML (`&`, `<`, `>`) no texto livre.
  - Converte cabeçalhos Markdown (`# Título`) para `<b>Título</b>`.
  - Converte negrito e itálico combinados (`***texto***`) para `<b><i>texto</i></b>`.
  - Converte negrito (`**texto**` e `__texto__`) para `<b>texto</b>`.
  - Converte itálico (`*texto*` e `_texto_` em palavras isoladas, mantendo `c6_joao` e identificadores snake_case intactos) para `<i>texto</i>`.
  - Converte tachado (`~~texto~~`) para `<s>texto</s>`.
  - Converte links (`[texto](url)`) para `<a href="url">texto</a>`.
  - Restaura blocos de código com tags suportadas pelo Telegram (`<pre><code class="...">` e `<code>`).
- **`send_agent_reply(...)`**:
  - Envia mensagens e fotos utilizando `ParseMode.HTML`.
  - Mantém fallback automático e seguro para texto puro caso o Telegram Server rejeite alguma formatação inesperada.

### 2.2. Atualização dos Handlers
- **[telegram_api/handlers/message_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/message_handler.py)**:
  - `handle_text_message` e `handle_agent_callback` agora utilizam `send_agent_reply`.
  - Remoção de lógica duplicada de envio e tratamento de erros.
- **[telegram_api/handlers/photo_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/photo_handler.py)**:
  - Padronização de imports no topo do arquivo (removendo `from telegram.error import BadRequest` de dentro da função).
  - Uso de `send_agent_reply`.
- **[telegram_api/handlers/voice_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/handlers/voice_handler.py)**:
  - Padronização de imports no topo do arquivo.
  - Uso de `send_agent_reply`.

---

## 3. Testes e Validação

1. **Testes Unitários do Formatador ([telegram_api/tests/core/test_formatter.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/tests/core/test_formatter.py))**:
   - 10 cenários testados: texto exato do erro, cabeçalhos, negrito duplo/simples, itálico, snake_case (`c6_joao`, `conta_bancaria_c6`), blocos de código com HTML interno, escape de tags perigosas, envio com sucesso e fallback em erro de parse.
2. **Testes Unitários dos Handlers**:
   - [telegram_api/tests/handlers/test_message_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/tests/handlers/test_message_handler.py)
   - [telegram_api/tests/handlers/test_photo_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/tests/handlers/test_photo_handler.py)
   - [telegram_api/tests/handlers/test_voice_handler.py](file:///Users/joaoflauzino/Documents/projetos/flauzino-assistant/telegram_api/tests/handlers/test_voice_handler.py)
3. **Execução de Testes e Linters**:
   - `pytest telegram_api/tests`: 34 testes passando.
   - `pytest` geral do repositório: 162 testes passando.
   - `make format` (`black`) e `make lint` (`ruff`): 0 erros, código 100% em conformidade com PEP 8.
