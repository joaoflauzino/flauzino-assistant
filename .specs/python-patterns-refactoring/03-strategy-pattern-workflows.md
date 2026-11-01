# Fase 3: Strategy Pattern em Ações de Lote, Commit de Transações e Gráficos

**Skill aplicada:** `python-pattern-strategy`  
**Serviços-alvo:** `finance_api` (`finance_api/services/imports.py`, `finance_api/services/import_strategies.py`) e `graph_api` (`graph_api/services/graph_service.py`, `graph_api/services/chart_strategies.py`)

---

## 1. Diagnóstico Detalhado (Estado Atual)

### 1.1. `ImportService.bulk_action` (`finance_api/services/imports.py`, linhas 497-576)
- Possui um bloco `if/elif/elif/elif/else` acoplado que trata 4 ações distintas (`"approve"`, `"ignore"`, `"reopen"`, `"set_category"`) com regras de validação, pulo (`skipped`), erro e aprendizado de regras (`rule_repo.upsert_rule`) misturadas dentro de um único `for`.

### 1.2. `ImportService.commit_approved` (`finance_api/services/imports.py`, linhas 597-699)
- Possui outro bloco `if/elif/elif` baseado em `tx.kind`:
  - `"EXPENSE"`: valida categoria, constrói `SpentCreate`, chama `spent_service.create`, atualiza `committed_spent_id`.
  - `"INCOME"`: valida categoria, constrói `IncomeCreate`, chama `income_service.create`, atualiza `committed_income_id`.
  - `("TRANSFER", "INVOICE_PAYMENT", "REFUND")`: marca como `COMMITTED` sem criar lançamento duplicado.

### 1.3. `graph_service.py` (`graph_api/services/graph_service.py`, linhas 9-108)
- Mistura a escolha de algoritmo de plotagem (`mode == "limites"` vs `mode == "saldo"` vs gráfico de pizza) com a renderização em bytes PNG (`fig.to_image`), dificultando a adição de novos tipos de gráficos (ex.: evolução mensal em linha, comparativo receitas vs. despesas).

---

## 2. Solução Proposta (Python 3.13+ Idiomático)

Seguindo as skills `python-pattern-strategy`, `python-modular-code-organization` e `python-zen-of-python` (*Flat is better than nested*), utilizamos `typing.Protocol` em `protocols.py`, `StrEnum`/`@dataclass` em `schemas/`, e um único módulo plano `finance_api/services/import_strategies.py` com **Tabelas de Despacho (`dict[str, Strategy]`)** para eliminar todas as escadas `if/elif/else`, sem criar subpacotes aninhados ou `__all__` redundantes.

---

### 2.1. Strategies para Ações em Lote e Commit (`finance_api/services/import_strategies.py`)

- **Bulk Action Strategies (`BulkActionStrategy` em `protocols.py`)**:
  - `ApproveBulkStrategy`
  - `IgnoreBulkStrategy`
  - `ReopenBulkStrategy`
  - `SetCategoryBulkStrategy`
  - `build_default_bulk_strategies(...)`
- **Commit Strategies (`TransactionCommitStrategy` em `protocols.py`)**:
  - `ExpenseCommitStrategy`: Valida `tx.category`, cria `SpentCreate`, chama `spent_service.create(...)` e preenche `tx.committed_spent_id`.
  - `IncomeCommitStrategy`: Valida `tx.category`, cria `IncomeCreate`, chama `income_service.create(...)` e preenche `tx.committed_income_id`.
  - `NonRecordCommitStrategy`: Usada para `TRANSFER`, `INVOICE_PAYMENT` e `REFUND`; apenas marca `tx.status = "COMMITTED"` e incrementa `processed_without_record`.
  - `build_default_commit_strategies(...)`

---

### 2.2. Strategy para Construção de Gráficos (`graph_api/services/chart_strategies.py`)

Na `graph_api`, separamos o contrato `ChartBuildStrategy` (`graph_api/services/protocols.py`), o enum `ChartMode` (`graph_api/schemas/graphs.py`) e os algoritmos de construção da figura (`go.Figure`) em `graph_api/services/chart_strategies.py` da renderização em imagem (`fig.to_image`) no `GraphRendererService` (`graph_api/services/graph_service.py`).

---

## 3. Checklist de Execução e Testes (Fase 3)

- [x] Criar `finance_api/services/import_strategies.py` (módulo plano coeso, sem subpacote desnecessário e sem `__all__`) com as 4 estratégias de ação em lote e as 3 estratégias de commit.
- [x] Isolar `BulkActionStrategy` e `TransactionCommitStrategy` em `finance_api/services/protocols.py` e DTOs/Enums em `finance_api/schemas/`.
- [x] Refatorar `ImportService.bulk_action` e `ImportService.commit_approved` para usar os dicionários de estratégia injetados.
- [x] Criar `graph_api/services/protocols.py`, `graph_api/services/chart_strategies.py` e `GraphRendererService` injetado via `Annotated[..., Depends(...)]` no router `graph_api/routers/graphs.py`.
- [x] Executar suíte de testes de `finance_api` e `graph_api` (`uv run pytest`).
