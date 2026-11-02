# Fase 0 — Pré-requisitos, Gates e Rede de Segurança

> **Spec:** [00-master-plan.md](./00-master-plan.md)
> **Status:** ✅ Concluída (2026-11-02) · (`⬜ Não iniciada` → `🟨 Em andamento` → `✅ Concluída`)
> **Depende de:** —
> **Commits previstos:** 2
> **Regra:** nenhuma refatoração acontece nesta fase.

---

## Tarefas

### 0.1 Destino do WIP atual (branch `feat/refactor`)
O working tree tinha alterações não commitadas em `finance_api/services/invoices.py`, `balances.py`, `dashboard_strategies.py` + testes (trabalho de fechamento de faturas). Nada da Fase 1 começa antes disso resolvido.

- [x] Rodar suíte completa sobre o WIP (`uv run pytest`) e garantir verde (504 passed)
- [x] Apresentar `git diff` e resumo ao desenvolvedor (`AGENTS.md` §7) — working tree já estava limpo: o WIP foi commitado em `0351f34` (`fix(dashboard): corrige período do ciclo de faturas no modo INVOICES`) e `e0ab5e6` (`feat(finance): improve invoice management...`); nenhum commit novo foi criado
- [x] Obter autorização explícita e commitar o WIP — não aplicável: nada pendente no working tree
- [x] **Re-medir** `invoices.py` e `balances.py` após o commit (resultado na seção "Re-medição" abaixo)

### 0.2 Gates de complexidade no `ruff` (`pyproject.toml`)
- [x] Medir o ruído das regras novas antes de fixar tetos
- [x] Configurar `PLR0912`/`PLR0915` com tetos permissivos (`max-branches = 8`, `max-statements = 50`)
- [x] Congelar a lista de violações atuais (dívida visível — mapa está no master plan §2): 1 violação de branches, congelada via `per-file-ignores` em `agent_api/services/agent.py` (será removida na Fase 1.1); 0 violações de statements
- [x] Avaliar `PLR0913` (max-args) — **não adotado**: 16 violações espalhadas por production e testes (`callbacks`, `routers`, `imports`, `staged_transactions`, etc.), ruído demais para o código-base inteiro

### 0.3 Testes de caracterização (rede de segurança)
- [x] `agent_api/tests/services/test_agent_service.py`: 3 vias de `_extract_assistant_response` + merge de `image_base64` (5 testes novos)
- [x] `finance_api/tests/services/test_invoices.py`: patch parcial (só closing, só due, status), invoice inexistente (criação com defaults), cartão sem `credit_card_id`, PM inexistente/não-cartão (6 testes novos)
- [x] `update()` de spents/incomes/subscriptions/credit_cards: categoria inválida, PM inválida, PM que resolve conta/cartão, entidade inexistente (+ repo retornando `None`) (19 testes novos)
- [x] `telegram_api/tests/services/test_session_service.py`: repo injetado vs default × complete vs session_id vs sem nada (3 testes novos)
- [x] `finance_api/tests/repositories/test_payment_methods_repository.py`: `get_by_key` achando em payment_methods, credit_cards, accounts e não achando (2 testes novos)

### 0.4 Verificação
- [x] `make format` && `make lint` && `uv run pytest` verdes (539 passed)

---

## Re-medição pós-WIP (`invoices.py` / `balances.py`)

Medição AST (apenas corpos de produção, `ast.If`; profundidade = `if`/`for`/`while`):

| Arquivo:linha | Função | LOC | `if`s | Prof. | Muda vs master plan? |
|---|---|---:|---:|---:|---|
| `finance_api/services/invoices.py:131` | `update_invoice_dates` | 43 | 6 | 3 | Profundidade 2 → **3** |
| `finance_api/services/balances.py:90` | `_resolve_pm_invoice_period` | 40 | 4 | 3 | Profundidade 2 → **3** |
| `finance_api/services/balances.py:138` | `_build_balances` | 44 | 1 | 3 | **Nova violação** (LOC > 40), não listada no master plan |

### Ruído medido para os gates (antes de fixar os tetos)

| Regra / teto | Violações hoje | Decisão |
|---|---:|---|
| `PLR0912` (default `max-branches=12`) | 0 | — |
| `PLR0912` com `max-branches=8` | 1 (`agent_api/services/agent.py:83`, 9 branches) | congelada em `per-file-ignores` (Fase 1.1) |
| `PLR0912` com `max-branches=6` (meta final) | 2 (`agent.py:83`, `finance_api/core/decorators.py:24`) | reduzir ao final das fases |
| `PLR0915` com `max-statements=50` | 0 | gate ativo, sem dívida |
| `PLR0915` com `max-statements=25` (diagnóstico) | 13 (10 em testes, 4 produção) | meta final é 40 |
| `PLR0913` (default `max-args=5`) | 16 (production + testes) | **não adotar** |

---

## Critérios de aceite da fase (gates)

- [x] WIP commitado **com autorização explícita** do desenvolvedor — já estava commitado (`0351f34`/`e0ab5e6`), working tree limpo
- [x] Gates `PLR0912`/`PLR0915` configurados e violações congeladas
- [x] Testes de caracterização dos 5 pontos críticos escritos e verdes
- [x] `invoices.py`/`balances.py` re-medidos (números atualizados no master plan)
- [x] Suíte completa verde

---

## Evidências de execução

| Data | Commit | Descrição | Testes |
|---|---|---|---|
| 2026-11-02 | `0351f34` (WIP já existente) | Working tree limpo; WIP de faturas/dashboard já commitado | 504 passed (baseline) |
| 2026-11-02 | (sem commit — aguardando autorização) | Gates `PLR0912`/`PLR0915` no `pyproject.toml` + 35 testes de caracterização | 539 passed · `black --check` limpo · `ruff check` limpo |
