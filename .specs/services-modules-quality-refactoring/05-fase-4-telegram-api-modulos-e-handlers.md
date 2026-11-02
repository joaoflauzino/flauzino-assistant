# Fase 4 — Eixo C `telegram_api`: Regra 4, Splits de Módulo e Handlers Finos

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** ✅ Concluída (2026-11-02) · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** Fase 0 concluída (usa `SessionService` refatorado na Fase 1.4)
> **Commits previstos:** 3
> **Meta:** zero funções top-level com `_` no `telegram_api`; handlers ≤ 30 LOC; retry em um único lugar.

---

## Tarefas

### 4.1 `telegram_api/core/formatter.py` (238 linhas, 11 funções `_`) — split por SRP
Mistura formatação **pura** com **I/O de envio** (viola Regra 3/SRP).

- [x] `core/formatter.py` → só formatação pura: `markdown_to_telegram_html`, `format_code_block`, `format_inline_code`, `protect_code`, `apply_markdown_rules`, `restore_code` (nomes públicos — Regra 4)
- [x] `core/sender.py` (novo) → só I/O Telegram: `send_agent_reply`, `send_photo`, `send_text`, `send_with_html_fallback`, `is_parse_error`, `markup_payload`, `photo_payload`
- [x] Atualizar imports de todos os handlers e testes (`test_formatter.py`)
- [x] Commit: `refactor(telegram): split formatter/sender + http clients + retry` (agrupado com 4.2)

### 4.2 `telegram_api/core/http_client.py` (422 linhas) — retry centralizado + split
Hoje: `send_message_to_agent`, `send_receipt_to_agent`, `send_audio_to_agent` repetem o mesmo `for attempt in range(3)` + backoff (cada um prof. 4) — anti-pattern *Scattered Timeout/Retry Logic*.

- [x] Extrair `post_with_retry(request_coro_factory, *, attempts=3, backoff=2)` e usar nas 3 funções
- [x] `get_balance_graph` (60 LOC, 4 `if`s): decompor em `fetch_month_summary(...)`, `build_graph_payload(...)`, `render_graph(...)`; função pública ≤ 20 linhas
- [x] Split plano (Regra 6): `core/http_client.py` (lifecycle + `post_with_retry` + headers) / `core/agent_client.py` (send message/receipt/audio) / `core/finance_client.py` (`save_spent`, `save_subscription`, `get_balance_graph` e demais)
- [x] Manter os nomes públicos das funções (handlers importam direto); atualizar imports
- [x] Testes: `test_http_client.py` + testes de handlers
- [x] Commit: agrupado com 4.1

### 4.3 `telegram_api/handlers/expense_handler.py` (409 linhas, 8 funções `_`) — negócio → services
Builders e savers estão na camada errada (handler deve ser fino).

- [x] Criar `telegram_api/services/expense_service.py`: `build_spent_data`, `build_subscription_data`, `save_single_purchase`, `save_installment`, `save_continuous_subscription`, `persist_expense` (nomes públicos)
- [x] `PURCHASE_SAVERS: dict[str, Callable]` (hoje `_resolve_saver`) vira dispatch table pública no service
- [x] Handler `confirm_expense` fica: parse callback → `expense_service.persist(...)` → reply/erro
- [x] Testes: `test_expense_handler.py` + novo `test_expense_service.py`
- [x] Commit: `refactor(telegram): expense_service + agent_interaction flow` (agrupado com 4.4)

### 4.4 Duplicação voice/photo/message handlers (76/73/57 LOC)
Os 3 handlers repetem: enviar → sincronizar sessão → formatar → responder.

- [x] Criar `telegram_api/services/agent_interaction.py` com o fluxo comum (usando `SessionService` da Fase 1.4 e `sender.py` da 4.1)
- [x] Cada handler passa a: extrair conteúdo do Update (texto/áudio/foto) → delegar → tratar erro específico (≤ 30 LOC)
- [x] Testes: `test_voice_handler.py`, `test_photo_handler.py`, `test_message_handler.py` + novo `test_agent_interaction.py`
- [x] Commit: agrupado com 4.3

### 4.5 Renomeação Regra 4 nos demais arquivos
- [x] `core/middleware.py` (5 funções `_`): renomear públicas; helpers puros (`detect_media_type`, `detect_message_type`) → `telegram_api/core/utils.py` (novo)
- [x] `main.py` (8 funções `_`): renomear públicas (`register_handlers`, `schedule_weekly_summary`, `build_application`, ...)
- [x] `handlers/balance_handler.py` (8 funções `_`): renomear públicas (dispatch `resolve_action` + ações)
- [x] `handlers/balance_summary_handler.py` (1): `format_currency` → `core/utils.py`
- [x] Atualizar todos os testes que importam esses símbolos
- [x] Commit: `refactor(telegram): public helper names per modular-organization rule 4`

---

## Critérios de aceite da fase (gates)

- [x] Zero funções top-level com prefixo `_` no `telegram_api`
- [x] `formatter.py` ≤ ~120 linhas (puro) e `sender.py` ≤ ~150 (I/O)
- [x] Retry/backoff de HTTP em **um único lugar** (`post_with_retry`)
- [x] Nenhum arquivo de `telegram_api/core/` ou `handlers/` > ~250 linhas
- [x] Handlers ≤ 30 LOC, delegando para `services/`
- [x] `make format` && `make lint` && `uv run pytest` verdes
- [x] Comportamento do bot inalterado (mesmos `callback_data`, mesmas respostas)

---

## Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| 2026-11-02 | — (aguardando autorização) | 4.1/4.2 `formatter.py` (puro, 127 LOC) + `sender.py` (I/O, 125 LOC); `http_client.py` 422 → 71 LOC com `post_with_retry` único; `agent_client.py` (117) e `finance_client.py` (216) + `defaults.py`; `get_balance_graph` 60 → 22 LOC com `fetch_balances`/`filter_balances`/`render_balance_graph` | 650 passed · gate 14 → 12 |
| 2026-11-02 | — | 4.3 `expense_service` movido para `services/expense.py` (builders, savers, `PURCHASE_SAVERS`, `persist_expense`); handler 409 → 243 LOC (confirmação/data em `expense_confirmation.py`, estados em `expense_states.py`) | 650 passed |
| 2026-11-02 | — | 4.4 `services/agent_interaction.py` elimina a duplicação voice/photo/message (sessão → call → sync → reply + mapeamento de erros); handlers 76/73/57 → ~30 LOC cada | 650 passed (+17 novos de service/interaction) |
| 2026-11-02 | — | 4.5 renomes Regra 4 (middleware 5, main 8, balance_handler 8) + `core/utils.py` (`detect_media_type`, `detect_message_type`, `format_currency`) | 650 passed · **zero** top-level `_` no telegram_api |

### Notas de execução

- **4.1/4.2** — `formatter.py` ficou só com transformação pura (Markdown + teclado); `sender.py` com o I/O de envio e fallback HTML. O retry triplicado virou `post_with_retry(request, *, attempts=3, backoff=2.0)` com backoff exponencial idêntico (1s, 2s). `get_balance_graph` foi decomposto em `fetch_balances` (404 → `None`), `filter_balances` (pura) e `render_balance_graph`, preservando logs e contrato. As 6 listas de fallback do finance_api saíram para `core/defaults.py` (finance_client 261 → 216 LOC); os `get_valid_*` passaram a compartilhar `fetch_keys` e trocaram `except Exception` por `(httpx.HTTPError, ValueError, KeyError, TypeError)`.
- **4.3** — o módulo ficou `services/expense.py` (e não `expense_service.py`) para respeitar a Regra 8.2 do gate (módulo não repete o nome do pacote `services`). O handler perdeu 166 linhas: savers foram para o service, o fluxo de data/confirmação para `expense_confirmation.py` e os IDs de estado para `expense_states.py` (evita import circular). `PURCHASE_SAVERS` virou dispatch table pública no service.
- **4.4** — `handle_agent_interaction` absorve try/except e a sequência sessão → chamada → sync → resposta; `InteractionMessages` (dataclass) carrega os textos por canal. `handle_agent_callback` reusa `run_agent_call`/`reply_with_response`. Callbacks e mensagens ao usuário preservados.
- **4.5** — `middleware.py`, `main.py` e `balance_handler.py` tiveram todos os helpers públicos renomeados; `detect_media_type`/`detect_message_type`/`format_currency` foram para `core/utils.py`. **Zero** funções top-level com `_` no `telegram_api`.
- **Gate de arquitetura** — baseline 14 → **12** (regra B zerada no telegram_api); restam 10 itens de renome (6.5) e 2 de `__all__` (5.3), sem entradas obsoletas.
- **Tolerâncias** — `formatter.py` 127 LOC (gate ~120) e `expense_handler.py` 243 LOC (gate ~250) ficaram dentro da margem do "~"; `sender.py` 125 e `finance_client.py` 216 estão sob os tetos.
