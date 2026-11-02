# Plano Diretor — Refatoração de Services (Condicionais/Métodos Longos) e Organização Modular

> **Objetivo:** reduzir `if`s encadeados e métodos longos nos **services** e corrigir a **má organização de módulos**, aplicando as skills oficiais do repositório (`python-pep8-guidelines`, `python-modular-code-organization`, `python-zen-of-python`, `python-anti-patterns`, `python-pattern-strategy`, `python-pattern-chain-of-responsibility`, `python-pattern-factory`, `python-pattern-repository-service`).
>
> **Branch de trabalho:** `feat/refactor` (3º ciclo — os planos anteriores `.specs/code-quality-refactoring/`, `.specs/quality-refactoring/` e `.specs/python-patterns-refactoring/` já foram em grande parte executados; este plano é **incremental** e parte do estado atual medido).
>
> **Status geral:** ⬜ Aguardando aprovação humana — nenhuma execução iniciada (`AGENTS.md` §6 e §7).

---

## 0. Acompanhamento (tracking)

### Como usar esta spec
1. Cada fase tem um arquivo próprio com **checklist de tarefas por commit** e **gates de aceite**.
2. Ao iniciar uma fase: mudar o `Status` do arquivo para `🟨 Em andamento`.
3. Ao concluir uma tarefa: marcar o checkbox, registrar data/commit/testes na tabela **Evidências de execução** do arquivo da fase.
4. Ao concluir a fase: fechar os gates, marcar `✅ Concluída` e atualizar a tabela abaixo.
5. **Nenhum commit/push sem autorização explícita** do desenvolvedor (`AGENTS.md` §7).

### Fases

| Fase | Arquivo | Escopo | Status | Progresso |
|---|---|---|---|---|
| 0 | [01-fase-0-gates-e-rede-de-seguranca.md](./01-fase-0-gates-e-rede-de-seguranca.md) | WIP atual, gates de lint, testes de caracterização | ⬜ Não iniciada | 0/4 tarefas |
| 1 | [02-fase-1-condicionais-em-services.md](./02-fase-1-condicionais-em-services.md) | Eixo A — cascatas de `if` nos services | ⬜ Não iniciada | 0/6 tarefas |
| 2 | [03-fase-2-metodos-longos-em-services.md](./03-fase-2-metodos-longos-em-services.md) | Eixo B — métodos > 40 LOC nos services | ⬜ Não iniciada | 0/6 tarefas |
| 3 | [04-fase-3-finance-api-repositorios-e-modulos.md](./04-fase-3-finance-api-repositorios-e-modulos.md) | Eixo C — `finance_api`: repositories, imports tardios, utils | ⬜ Não iniciada | 0/6 tarefas |
| 4 | [05-fase-4-telegram-api-modulos-e-handlers.md](./05-fase-4-telegram-api-modulos-e-handlers.md) | Eixo C — `telegram_api`: Regra 4, splits, handlers finos | ⬜ Não iniciada | 0/5 tarefas |
| 5 | [06-fase-5-agent-api-e-verificacao-final.md](./06-fase-5-agent-api-e-verificacao-final.md) | Eixo C — `agent_api`, `__all__`, verificação final | ⬜ Não iniciada | 0/4 tarefas |

### Definição de pronto global

- [ ] Fase 0 — gates e rede de segurança
- [ ] Fase 1 — condicionais em services
- [ ] Fase 2 — métodos longos em services
- [ ] Fase 3 — `finance_api` modular
- [ ] Fase 4 — `telegram_api` modular
- [ ] Fase 5 — `agent_api` modular + verificação final

---

## 1. Princípios que guiam este plano

1. **Máximo 3 condicionais por função** (`AGENTS.md` §3.4) — guard clauses e retorno antecipado primeiro (`python-zen-of-python`: *Flat is better than nested*).
2. **Métodos > ~40 linhas são candidatos a decomposição** (SRP — `python-pep8-guidelines` §5).
3. **Cascata de `if/elif` sobre um discriminador → dispatch table / Strategy** (`python-pattern-strategy`).
4. **Patch campo-a-campo (`if data.x is not None`) → declarativo** (`model_dump(exclude_unset=True)` ou dict comprehension) — Regra 7 do `python-modular-code-organization`.
5. **Funções standalone nunca começam com `_`** — Regra 4 do `python-modular-code-organization`: helpers puros vão para `utils.py` com nome público.
6. **Imports exclusivamente no topo do arquivo** (`AGENTS.md` §3.4) — zero imports tardios dentro de funções.
7. **Zero `except Exception` engolindo erro** (`python-anti-patterns`) — exceções específicas, logadas e reerguidas.
8. **Read Before Write / Nenhuma mudança de comportamento:** refatoração pura; bugs encontrados no caminho viram commit separado.
9. **Uma fase = um PR/commit independente**, com `make format` + `make lint` + `uv run pytest` verdes. Não misturar fases.

---

## 2. Linha de base medida (working tree atual, AST scan sem testes)

- **904 funções de produção** nas 4 APIs.
- **33 funções violando os gates** (`ifs > 3` OU `loc > 40` OU `profundidade ≥ 4`).
- **~50% das violações (17) estão na camada `services/`** — foco pedido pelo desenvolvedor.
- **56 funções top-level com `_underscore`** em 16 arquivos (violação da Regra 4).
- **6 imports tardios** dentro de funções em `finance_api/repositories/` (violação do `AGENTS.md` §3.4).
- **3 `__all__`** em `__init__.py` internos (violação da Regra 5).

### 2.1 Piores funções por densidade de condicionais (Eixo A)

| Arquivo:linha | Função | LOC | `if`s | Prof. | Problema central | Fase |
|---|---|---:|---:|---:|---|---|
| `agent_api/services/agent.py:83` | `_extract_assistant_response` | 49 | 7 | 5 | 3 estratégias de extração em cascata + merge de `image_base64` repetido 3× | 1.1 |
| `finance_api/services/invoices.py:131` | `update_invoice_dates` | 43 | 6 | 2 | patch vs criação + patch campo-a-campo (Regra 7) — **WIP não commitado** | 1.2 |
| `finance_api/repositories/staged_transactions.py:101` | `list_by_filter` | 54 | 6 | 1 | condições + paginação inline | 3.4 |
| `finance_api/services/spents.py:216` | `update` | 30 | 6 | 2 | orquestração validação categoria → PM → resolver → patch | 1.3 |
| `finance_api/services/incomes.py:122` | `update` | 16 | 5 | 3 | mesmo padrão duplicado do `spents.update` | 1.3 |
| `finance_api/services/subscriptions.py:78` | `update` | 23 | 5 | 2 | idem + instancia `CategoryRepository` no método (viola DI) | 1.3 |
| `finance_api/services/credit_cards.py:64` | `update` | 20 | 5 | 2 | idem | 1.3 |
| `telegram_api/services/session_service.py:35` | `sync_chat_session` | 23 | 5 | 3 | branch "repo injetado vs default" duplica delete/save | 1.4 |
| `finance_api/services/import_strategies.py:113` | `SetCategoryBulkStrategy.execute` | 38 | 5 | 1 | validação EXPENSE/INCOME duplicada | 1.5 |
| `telegram_api/core/http_client.py:362` | `get_balance_graph` | 60 | 4 | 1 | fetch + payload + graph + erros inline | 4.2 |
| `finance_api/services/balances.py:90` | `_resolve_pm_invoice_period` | 40 | 4 | 2 | **WIP não commitado** — reavaliar | 1.6 |
| `finance_api/repositories/payment_methods.py:28` | `get_by_key` | 52 | 3 | 2 | 2× `try/except Exception` + imports tardios + `getattr` defensivo | 3.1 |

### 2.2 Métodos longos sem excesso de `if` (Eixo B — SRP/tamanho)

| Arquivo:linha | Função | LOC | Problema central | Fase |
|---|---|---:|---|---|
| `finance_api/services/imports.py:57` | `ImportService.__init__` | 97 | 16 parâmetros + wiring manual de 8 colaboradores | 2.1 |
| `telegram_api/handlers/voice_handler.py:16` | `handle_voice_message` | 76 | parse + sessão + agent + formatação + reply no handler | 4.4 |
| `telegram_api/handlers/photo_handler.py:16` | `handle_photo_message` | 73 | idem (duplicação voice/photo/message) | 4.4 |
| `finance_api/repositories/payment_methods.py:81` | `list` | 56 | query + filtros + merge de fontes inline | 3.1 |
| `telegram_api/handlers/message_handler.py:33` | `handle_text_message` | 57 | idem voice/photo | 4.4 |
| `finance_api/importers/c6_credit_card_csv.py:93` | `_parse_row` | 50 | mapping com muitos campos (baixa complexidade) | 2.6 (documentar) |
| `agent_api/services/tools/graph.py:18` | `build_gerar_grafico` | 51 | closure + função interna longa (docstring = contrato LLM) | 2.5 |
| `agent_api/services/ocr.py:63` | `extract_text` | 46 | I/O + validação + pytesseract + limpeza | 2.2 |
| `finance_api/services/incomes.py:148` | `get_monthly_summary` | 45 | fetch + agregações + montagem | 2.3 |
| `finance_api/services/import_staging.py:94` | `_to_staged` | 45 | mapping puro (0 `if`) | 2.6 (documentar) |
| `finance_api/services/ai_classifier.py:17` | `classify_batch` | 43 | payload + LLM + sanitize no mesmo método | 2.4 |

### 2.3 Organização modular (Eixo C — `python-modular-code-organization`)

| Violação | Regra | Onde | Fase |
|---|---|---|---|
| **56 funções top-level com `_`** | Regra 4 | `telegram_api/core/formatter.py` (11), `handlers/balance_handler.py` (8), `handlers/expense_handler.py` (8), `telegram_api/main.py` (8), `core/middleware.py` (5), `agent_api/core/callbacks.py` (5), `agent_api/services/classify.py` (2), + 9 arquivos com 1 cada | 4.1–4.5, 5.1–5.2 |
| **Imports tardios em funções** | `AGENTS.md` §3.4 | `finance_api/repositories/payment_methods.py` (5×), `categories.py` (1×: linha 35) | 3.1–3.2 |
| **`__all__` em módulos internos** | Regra 5 | `finance_api/models/__init__.py`, `agent_api/services/tools/__init__.py`, `telegram_api/services/__init__.py` | 3.6, 5.3 |
| **Utilidade duplicada em vez de `utils.py`** | Regra 3 | `_normalize_str`/`_normalize` em 3 repositories — já existe `finance_api/utils/text.py` (repos usam `.lower()`, utils `.upper()` — preservar call-site) + alias `_normalize` em `utils/text.py:13` | 3.3 |
| **Módulo com SRP misto (formatação pura + I/O)** | Regra 3/SRP | `telegram_api/core/formatter.py` (238 linhas) | 4.1 |
| **Retry loop duplicado 3×** | `python-anti-patterns` | `telegram_api/core/http_client.py`: mesmo `for attempt in range(3)` + backoff em 3 funções (prof. 4) | 4.2 |
| **Lógica de negócio no handler** | Camadas | `telegram_api/handlers/expense_handler.py` (409 linhas): builders e savers deveriam estar em `services/` | 4.3 |
| **Arquivos acima do teto (~300 linhas, Regra 6)** | Regra 6 | `http_client.py` (422), `expense_handler.py` (409), `import_strategies.py` (349), `core/dependencies.py` (306) | 3.5, 4.2–4.3 |
| **Instanciação de dependência dentro de método** | DI (`AGENTS.md` §3.4) | `finance_api/services/subscriptions.py:84` | 1.3 |
| **`getattr` defensivo contra mocks em produção** | `python-anti-patterns` | `payment_methods.py:48,68`, `spents.py:230` | 1.3, 3.1 |

---

## 3. Ordem de execução sugerida (commits pequenos)

1. `chore(lint): add PLR0912/PLR0915 gates and freeze baseline` (Fase 0)
2. `test(services): characterization tests for update/extract/sync flows` (Fase 0)
3. `refactor(agent): chain-of-responsibility in _extract_assistant_response` (1.1)
4. `refactor(invoices): split patch vs create + declarative patch` (1.2)
5. `refactor(services): extract UpdateDataPreparer from update() family` (1.3)
6. `refactor(telegram): session_service repository scope` (1.4)
7. `refactor(imports): kind dispatch in SetCategoryBulkStrategy` (1.5)
8. `refactor(imports): factory for ImportService wiring` (2.1)
9. `refactor(services): decompose long methods (ocr, incomes, ai_classifier, graph tool)` (2.2–2.5)
10. `refactor(repositories): payment_methods lookup chain + top-level imports` (3.1–3.2)
11. `refactor(utils): consolidate text normalization` (3.3)
12. `refactor(repositories): staged_transactions conditions/pagination` (3.4)
13. `refactor(imports): split import_strategies into bulk/commit modules` (3.5)
14. `refactor(telegram): split formatter/sender + http clients + retry` (4.1–4.2)
15. `refactor(telegram): expense_service + agent_interaction flow` (4.3–4.4)
16. `refactor(telegram): public helper names per modular-organization rule 4` (4.5)
17. `refactor(agent): core/utils + services/utils + remove __all__` (5.1–5.3)

Cada commit: `make format` + `make lint` + `uv run pytest` verdes. **Nenhum commit/push sem autorização explícita** (`AGENTS.md` §7).

---

## 4. Definição de pronto global (quality gates)

- [ ] Nenhuma função de produção com **> 3 condicionais** (`AGENTS.md` §3.4) — ou justificativa documentada (Fase 2.6).
- [ ] Nenhuma função de produção com **> 40 LOC**, salvo casos documentados.
- [ ] Nenhuma função com **profundidade de aninhamento ≥ 4**.
- [ ] **Zero** funções top-level com prefixo `_` (Regra 4).
- [ ] **Zero** imports fora do topo do arquivo (`AGENTS.md` §3.4).
- [ ] **Zero** `except Exception` engolindo erro em repositories/services.
- [ ] **Zero** `__all__` em módulos internos (Regra 5).
- [ ] Retry/backoff de HTTP em **um único lugar** no `telegram_api`.
- [ ] Handlers do Telegram ≤ 30 LOC, delegando para `services/`.
- [ ] `ruff` (`C90`, `PLR0912`, `PLR0915`) sem violações; `make format`, `make lint`, `uv run pytest` verdes.
- [ ] Testes unitários atualizados/criados para cada colaborador extraído (fakes/mocks, sem banco real).
- [ ] Nenhuma mudança de contrato HTTP externo.
- [ ] `git diff` apresentado ao usuário antes de qualquer commit.

---

## 5. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| WIP atual (invoices/balances/dashboard) conflitar com a Fase 1 | Fase 0 exige commit do WIP antes; re-medir `invoices.py`/`balances.py` após |
| Renomear 56 funções `_` quebrar imports em testes/handlers | Renomeação por fase e por API; `grep` global + suíte completa a cada commit |
| Mover imports em `payment_methods.py` revelar dependência circular | Se houver ciclo, quebrar via `TYPE_CHECKING` ou mover adapter para módulo próprio — nunca manter import tardio |
| Remover `__all__`/re-exports de `models/__init__.py` quebrar registro SQLAlchemy | Validar `create_all`/migrations e imports em `main.py` antes; manter imports (remover só o `__all__`) |
| Split de `http_client.py` quebrar handlers do Telegram | Manter nomes públicos das funções; atualizar imports dos handlers no mesmo commit; `test_http_client.py` cobre |
| Docstrings de `@tool` (agent_api) alterarem comportamento do LLM | Decompor apenas o corpo; docstring e assinatura da tool permanecem idênticas |
| Scope creep | Cada fase é isolada; bugs encontrados viram issue/commit separado |

---

## 6. Referências das skills aplicadas

- `python-pep8-guidelines` → limite de condicionais, tipagem, imports no topo, SRP.
- `python-modular-code-organization` → Regra 3 (`utils.py`), Regra 4 (sem `_` top-level), Regra 5 (sem `__all__` interno), Regra 6 (arquivos planos ≤ ~300 linhas), Regra 7 (patch declarativo).
- `python-zen-of-python` → *Flat is better than nested*, *Errors should never pass silently*, *Simple is better than complex*.
- `python-anti-patterns` → scattered retry, bare/broad except, mixed I/O e lógica, DI.
- `python-pattern-strategy` → dispatch por `TransactionKind`, `PURCHASE_SAVERS`.
- `python-pattern-chain-of-responsibility` → extração de resposta do agente, lookup chain de payment methods.
- `python-pattern-factory` → `build_default_import_service`.
- `python-pattern-repository-service` → `UpdateDataPreparer`, fronteiras de camada no `telegram_api`.
