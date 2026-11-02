# Fase 4 — Eixo C `telegram_api`: Regra 4, Splits de Módulo e Handlers Finos

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** ⬜ Não iniciada · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** Fase 0 concluída (usa `SessionService` refatorado na Fase 1.4)
> **Commits previstos:** 3
> **Meta:** zero funções top-level com `_` no `telegram_api`; handlers ≤ 30 LOC; retry em um único lugar.

---

## Tarefas

### 4.1 `telegram_api/core/formatter.py` (238 linhas, 11 funções `_`) — split por SRP
Mistura formatação **pura** com **I/O de envio** (viola Regra 3/SRP).

- [ ] `core/formatter.py` → só formatação pura: `markdown_to_telegram_html`, `format_code_block`, `format_inline_code`, `protect_code`, `apply_markdown_rules`, `restore_code` (nomes públicos — Regra 4)
- [ ] `core/sender.py` (novo) → só I/O Telegram: `send_agent_reply`, `send_photo`, `send_text`, `send_with_html_fallback`, `is_parse_error`, `markup_payload`, `photo_payload`
- [ ] Atualizar imports de todos os handlers e testes (`test_formatter.py`)
- [ ] Commit: `refactor(telegram): split formatter/sender + http clients + retry` (agrupado com 4.2)

### 4.2 `telegram_api/core/http_client.py` (422 linhas) — retry centralizado + split
Hoje: `send_message_to_agent`, `send_receipt_to_agent`, `send_audio_to_agent` repetem o mesmo `for attempt in range(3)` + backoff (cada um prof. 4) — anti-pattern *Scattered Timeout/Retry Logic*.

- [ ] Extrair `post_with_retry(request_coro_factory, *, attempts=3, backoff=2)` e usar nas 3 funções
- [ ] `get_balance_graph` (60 LOC, 4 `if`s): decompor em `fetch_month_summary(...)`, `build_graph_payload(...)`, `render_graph(...)`; função pública ≤ 20 linhas
- [ ] Split plano (Regra 6): `core/http_client.py` (lifecycle + `post_with_retry` + headers) / `core/agent_client.py` (send message/receipt/audio) / `core/finance_client.py` (`save_spent`, `save_subscription`, `get_balance_graph` e demais)
- [ ] Manter os nomes públicos das funções (handlers importam direto); atualizar imports
- [ ] Testes: `test_http_client.py` + testes de handlers
- [ ] Commit: agrupado com 4.1

### 4.3 `telegram_api/handlers/expense_handler.py` (409 linhas, 8 funções `_`) — negócio → services
Builders e savers estão na camada errada (handler deve ser fino).

- [ ] Criar `telegram_api/services/expense_service.py`: `build_spent_data`, `build_subscription_data`, `save_single_purchase`, `save_installment`, `save_continuous_subscription`, `persist_expense` (nomes públicos)
- [ ] `PURCHASE_SAVERS: dict[str, Callable]` (hoje `_resolve_saver`) vira dispatch table pública no service
- [ ] Handler `confirm_expense` fica: parse callback → `expense_service.persist(...)` → reply/erro
- [ ] Testes: `test_expense_handler.py` + novo `test_expense_service.py`
- [ ] Commit: `refactor(telegram): expense_service + agent_interaction flow` (agrupado com 4.4)

### 4.4 Duplicação voice/photo/message handlers (76/73/57 LOC)
Os 3 handlers repetem: enviar → sincronizar sessão → formatar → responder.

- [ ] Criar `telegram_api/services/agent_interaction.py` com o fluxo comum (usando `SessionService` da Fase 1.4 e `sender.py` da 4.1)
- [ ] Cada handler passa a: extrair conteúdo do Update (texto/áudio/foto) → delegar → tratar erro específico (≤ 30 LOC)
- [ ] Testes: `test_voice_handler.py`, `test_photo_handler.py`, `test_message_handler.py` + novo `test_agent_interaction.py`
- [ ] Commit: agrupado com 4.3

### 4.5 Renomeação Regra 4 nos demais arquivos
- [ ] `core/middleware.py` (5 funções `_`): renomear públicas; helpers puros (`detect_media_type`, `detect_message_type`) → `telegram_api/core/utils.py` (novo)
- [ ] `main.py` (8 funções `_`): renomear públicas (`register_handlers`, `schedule_weekly_summary`, `build_application`, ...)
- [ ] `handlers/balance_handler.py` (8 funções `_`): renomear públicas (dispatch `resolve_action` + ações)
- [ ] `handlers/balance_summary_handler.py` (1): `format_currency` → `core/utils.py`
- [ ] Atualizar todos os testes que importam esses símbolos
- [ ] Commit: `refactor(telegram): public helper names per modular-organization rule 4`

---

## Critérios de aceite da fase (gates)

- [ ] Zero funções top-level com prefixo `_` no `telegram_api`
- [ ] `formatter.py` ≤ ~120 linhas (puro) e `sender.py` ≤ ~150 (I/O)
- [ ] Retry/backoff de HTTP em **um único lugar** (`post_with_retry`)
- [ ] Nenhum arquivo de `telegram_api/core/` ou `handlers/` > ~250 linhas
- [ ] Handlers ≤ 30 LOC, delegando para `services/`
- [ ] `make format` && `make lint` && `uv run pytest` verdes
- [ ] Comportamento do bot inalterado (mesmos `callback_data`, mesmas respostas)

---

## Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| — | — | — | — |
