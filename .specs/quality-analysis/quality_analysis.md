# 🔍 Análise de Qualidade — Flauzino Assistant

> Análise focada em: Qualidade de Código, Desacoplamento, Extensibilidade e Observabilidade.
> Gerado em: 2026-09-26

---

## 1. Qualidade de Código

### ✅ Pontos Fortes

| Aspecto | Avaliação |
|---|---|
| Type hints | ✅ Consistentes em todo o projeto |
| Imports no topo | ✅ Seguidos corretamente |
| Funções com docstring | ✅ Bom nível de cobertura |
| Tamanho das funções | ✅ Geralmente pequenas e focadas |
| Padrão de layers (route → service → repo) | ✅ Bem respeitado na `finance_api` e `agent_api` |
| Decorators para error handling | ✅ Excelente uso com `@handle_service_errors`, `@handle_finance_errors`, etc. |
| Async/await | ✅ Padrão assíncrono seguido em todos os serviços |

### ⚠️ Problemas Identificados

#### 1.1 Duplicação de lógica de sessão nos handlers do Telegram

Os arquivos `telegram_api/handlers/message_handler.py`, `voice_handler.py` e `photo_handler.py` têm **exatamente o mesmo padrão** de código repetido:

```python
# Nos 3 handlers (message, voice, photo):
async with get_db() as session:
    repo = SessionRepository(session)
    session_id = await repo.get_session(chat_id)
    # ... chama agent
    if is_complete:
        await repo.delete_session(chat_id)
    else:
        new_session_id = response_data.get("session_id")
        if new_session_id:
            await repo.save_session(chat_id, new_session_id)
```

**Problema:** O gerenciamento de sessão está triplicado. Qualquer mudança no fluxo de sessão precisa ser feita em 3 lugares.

**Solução:** Extrair para um helper `manage_agent_session(chat_id, response_data, repo)` em `telegram_api/services/` ou em um módulo utilitário de sessão.

#### 1.2 `handle_text_message` e `handle_agent_callback` têm lógica duplicada

O trecho de construção do `InlineKeyboardMarkup` a partir de `suggested_options` aparece idêntico em ambas as funções em `message_handler.py` (linhas 76–87 e 161–172).

```python
# Duplicado em handle_text_message e handle_agent_callback:
if suggested_options and isinstance(suggested_options, list):
    keyboard = []
    row = []
    for option in suggested_options:
        row.append(InlineKeyboardButton(option, callback_data=f"agent_opt:{option}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    reply_markup = InlineKeyboardMarkup(keyboard)
```

**Solução:** Mover para `telegram_api/core/formatter.py` como função `build_options_keyboard(options: list[str]) -> InlineKeyboardMarkup`.

#### 1.3 Imports dentro de função em `main.py`

Em `telegram_api/main.py`, a função `send_weekly_balance_summary` faz **imports tardios** dentro do corpo da função (linhas 124, 140 e 164):

```python
async def send_weekly_balance_summary(context) -> None:
    import httpx         # ❌ Import dentro de função
    ...
    import base64        # ❌ Import dentro de função
    ...
    from telegram_api.core.database import get_db  # ❌ Import dentro de função
    from sqlalchemy import text
```

Isso viola a regra do `AGENTS.md`: _"Jamais os imports podem ficar espalhados ou no meio do código"_.

**Solução:** Mover todos os imports para o topo do arquivo.

#### 1.4 `balance_handler.py` instancia `httpx.AsyncClient` diretamente no handler

A função `select_category` em `balance_handler.py` (linhas 108–163) cria um cliente HTTP avulso em vez de usar a abstração de `http_client.py`, que já gerencia o client compartilhado com connection pool.

```python
# ❌ balance_handler.py — cliente avulso sem pool, sem retry
async with httpx.AsyncClient(timeout=15.0) as client:
    fin_resp = await client.get(finance_url)
    response = await client.post(graph_url, json={...})
```

Compare com o padrão correto já adotado em `expense_handler.py`:

```python
# ✅ expense_handler.py — usa a abstração do http_client.py
from telegram_api.core.http_client import save_spent, save_subscription
await save_spent(spent_data)
```

**Solução:** Criar a função `get_balance_graph(categories: set[str], mode: str) -> bytes` em
`telegram_api/core/http_client.py`, encapsulando as chamadas às duas APIs (finance e graph).
O handler passa a chamar apenas essa função.

```python
# ✅ Como ficaria o balance_handler.py:
from telegram_api.core.http_client import get_balance_graph

img_data = await get_balance_graph(selected, mode)
await update.effective_message.reply_photo(photo=img_data, caption=f"Aqui está o gráfico de {mode}.")
```

#### 1.5 `send_weekly_balance_summary` duplica lógica do `balance_handler`

A função `send_weekly_balance_summary` em `main.py` repete a mesma lógica de buscar saldo e gerar
gráfico do `balance_handler.py`, criando mais um cliente HTTP avulso. Se a função `get_balance_graph()`
do item 1.4 for criada, ela resolve esse problema também.

---

## 2. Desacoplamento dos Serviços

### ✅ Pontos Fortes

- `finance_api`, `agent_api` e `telegram_api` são processos independentes comunicados por HTTP. ✅
- `agent_api` injeta serviços via `__init__` (`FinanceService`, `GraphService`) — injeção de dependência. ✅
- `finance_api` tem seu próprio sistema de exceções e handlers centralizados. ✅
- `AgentService.get_response()` recebe `platform` como parâmetro — consciente de multi-plataforma. ✅

### 📐 Decisão Arquitetural Validada: dois fluxos para a `finance_api`

A `telegram_api` acessa a `finance_api` por dois caminhos distintos, e isso é **intencional e correto**:

```
# Fluxo AI (linguagem natural):
telegram_api ──► agent_api ──► finance_api

# Fluxo Command (interface estruturada com botões Telegram):
telegram_api ──────────────► finance_api
```

**Justificativa:** Os handlers `/gasto` e `/saldo` oferecem uma experiência de UI estruturada com
`ConversationHandler` e botões inline — algo específico do Telegram que não faz sentido passar pelo
`agent_api` (adicionaria latência de LLM desnecessária e quebraria o controle de estado da conversa).
Cada canal futuro (WhatsApp, Discord) teria suas próprias particularidades de UI e implementaria
seu próprio acesso à `finance_api`.

**O único problema** nesse acesso direto é a forma: o `balance_handler.py` cria um cliente HTTP avulso
em vez de usar a abstração de `http_client.py` (descrito no item 1.4).

### ⚠️ Problema Identificado

#### 2.1 `telegram_api/services/` está vazia

O diretório `telegram_api/services/` existe mas está **completamente vazio**. A lógica repetida de
gerenciamento de sessão dos handlers (item 1.1) deveria estar aqui centralizada.

---

## 3. Extensibilidade — Adicionar um novo canal (ex: WhatsApp, Discord)

### Diagnóstico

A `agent_api` foi bem desenhada para ser agnóstica de plataforma:
- Aceita `platform` como parâmetro no endpoint `/chat`
- `AgentService.get_system_prompt()` já tem branches para `"telegram"` e `"web"`

Para adicionar um novo canal, o cenário esperado é:

```
whatsapp_api/
  handlers/
    expense_handler.py   # particularidades de menu WhatsApp
    balance_handler.py   # particularidades de UI WhatsApp
  core/
    http_client.py       # chama finance_api e agent_api
```

Cada canal tem suas próprias particularidades de UI — **isso é correto e esperado**. O que todos
compartilham é o *contrato* HTTP da `finance_api` e da `agent_api`, não a implementação.

**Obstáculos atuais para adicionar um novo canal:**

| Problema | Impacto |
|---|---|
| Lógica de sessão triplicada nos handlers | Dificuldade de entender o padrão correto a replicar |
| `balance_handler` com cliente HTTP avulso | Padrão incorreto que poderia ser copiado no novo canal |
| `send_weekly_balance_summary` embutida no `main.py` do Telegram | Funcionalidade de notificação acoplada ao canal |

**Nota positiva:** Com as correções dos itens 1.1 a 1.5 aplicadas, a extensibilidade melhora
significativamente — o padrão correto fica claro e fácil de replicar em um novo canal.

---

## 4. Observabilidade

### ✅ Pontos Fortes

| Componente | O que funciona bem |
|---|---|
| `AgentLoggingCallbackHandler` | Excelente — loga início/fim/erro de cada chamada LLM e tool com timing |
| `FinanceService._post_to_finance_api()` | Loga URL, payload, status e ID gerado |
| `ChatService.process_message()` | Loga entrada e saída com session_id, plataforma e resposta truncada |
| `agent.py get_response()` | Logs detalhados com prefixes `🔍`, `🎯`, `⚠️` para facilitar rastreamento |
| Decorators de erro | Capturam e logam exceções inesperadas com `exc_info=True` |

### ⚠️ Gaps de Observabilidade

#### 4.1 Sem correlation ID / request ID

Não existe um identificador único de requisição que percorra todos os serviços. Se uma interação
passa por `telegram_api → agent_api → finance_api`, não é possível correlacionar os logs dos 3
serviços para uma mesma requisição.

```
# Você vê no telegram_api:
[INFO] Received message from chat 12345: "registrar gasto..."
[INFO] Sent response to chat 12345

# Você vê no agent_api:
[INFO] 💬 [CHAT:IN] Sessão: abc-123 | Plataforma: telegram | Mensagem: ...

# Mas não dá pra saber que são a MESMA requisição sem cruzar manualmente
```

**Solução:** Gerar um `X-Request-ID` (UUID) no handler do Telegram e propagá-lo como header HTTP
para a `agent_api`, que por sua vez o propaga para a `finance_api`. Logar o `request_id` em cada serviço.

#### 4.2 `telegram_api` não tem log de tempo de resposta

Os handlers do Telegram não medem nem logam quanto tempo levou a chamada ao `agent_api`. Não é
possível saber se o bot está lento por causa do LLM, da rede ou do banco.

**Solução:** Adicionar `time.perf_counter()` antes e depois da chamada ao `send_message_to_agent()`
e logar o tempo total.

#### 4.3 Sem log estruturado (JSON)

Todos os logs são strings de texto livre. Em produção com stacks como Grafana/Loki ou Datadog, logs
em **JSON estruturado** são muito mais fáceis de filtrar, agregar e criar alertas.

```python
# Atual (texto livre):
logger.info(f"💬 [CHAT:IN] Sessão: {session_id} | Plataforma: {platform}")

# Ideal para produção (JSON estruturado via python-json-logger):
logger.info("chat_in", extra={"session_id": str(session_id), "platform": platform, "message_length": len(message)})
```

#### 4.4 Log format diferente entre `telegram_api` e `agent_api`

```python
# telegram_api/core/logger.py:
"[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"

# agent_api/core/logger.py:
"%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

Dois formatos diferentes dificultam a leitura unificada dos logs em produção.

---

## 5. Sumário Executivo

### Scorecard

| Dimensão | Nota | Principais Issues |
|---|---|---|
| **Qualidade de Código** | 🟡 7/10 | Imports dentro de funções, duplicação de sessão, builder de teclado duplicado |
| **Desacoplamento** | 🟢 8/10 | Sólido. Único problema: `balance_handler` usa `httpx` avulso em vez do `http_client.py` |
| **Extensibilidade** | 🟡 7/10 | `agent_api` totalmente preparada; `telegram_api` precisa do padrão de sessão centralizado |
| **Observabilidade** | 🟡 7/10 | Boa dentro de cada serviço, mas sem correlation ID entre serviços |

### Top 5 Ações de Maior Impacto (Prioridade)

1. **🔴 [Alta]** Criar `get_balance_graph(categories, mode)` em `http_client.py` e refatorar
   `balance_handler.py` para usá-la — elimina cliente HTTP avulso e a duplicação com
   `send_weekly_balance_summary`.
2. **🔴 [Alta]** Extrair gerenciamento de sessão repetido para um helper em `telegram_api/services/`
   — elimina triplicação em `message_handler`, `voice_handler` e `photo_handler`.
3. **🟠 [Média]** Mover imports para o topo em `send_weekly_balance_summary` no `main.py`
   (viola `AGENTS.md`).
4. **🟠 [Média]** Extrair `build_options_keyboard()` para `formatter.py` — elimina duplicação
   em `message_handler`.
5. **🟡 [Baixa]** Padronizar formato de log entre serviços e adicionar `X-Request-ID` para
   correlação entre serviços em produção.
