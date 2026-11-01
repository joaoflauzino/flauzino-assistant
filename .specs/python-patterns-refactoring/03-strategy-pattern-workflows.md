# Fase 3: Strategy Pattern em Ações de Lote, Commit de Transações e Gráficos

**Skill aplicada:** `python-pattern-strategy`  
**Serviços-alvo:** `finance_api` (`finance_api/services/imports.py`) e `graph_api` (`graph_api/services/graph_service.py`)

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

Seguindo a skill `python-pattern-strategy`, utilizaremos `typing.Protocol`, `StrEnum` e **Tabelas de Despacho (`dict[StrEnum, Strategy]`)** para eliminar todas as escadas `if/elif/else`.

---

### 2.1. Strategy para Ações em Lote (`finance_api/services/strategies/bulk_actions.py`)

```python
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.schemas.imports import BulkActionRequest


class BulkActionType(StrEnum):
    APPROVE = "approve"
    IGNORE = "ignore"
    REOPEN = "reopen"
    SET_CATEGORY = "set_category"


@dataclass(frozen=True)
class StepOutcome:
    status: str  # "updated" | "skipped" | "error"
    error_message: str | None = None


# ---------------------------------------------------------------------------
# 1. Strategy Interface (Protocol)
# ---------------------------------------------------------------------------
class BulkActionStrategy(Protocol):
    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome:
        ...


# ---------------------------------------------------------------------------
# 2. Concrete Strategies (Sem herança; validadas por subtipagem estrutural)
# ---------------------------------------------------------------------------
class ApproveBulkStrategy:
    def __init__(self, rule_repo: CategoryRuleRepositoryProtocol) -> None:
        self._rule_repo = rule_repo

    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome:
        if tx.possible_duplicate_of_spent_id or tx.possible_duplicate_of_income_id:
            return StepOutcome(status="skipped")
        if tx.kind in ("EXPENSE", "INCOME") and not tx.category:
            return StepOutcome(status="skipped")

        tx.status = "APPROVED"
        if req.remember and tx.category and tx.merchant:
            await self._rule_repo.upsert_rule(
                pattern=tx.merchant,
                direction=tx.direction,
                kind=tx.kind,
                category=tx.category,
                source="LEARNED",
            )
        return StepOutcome(status="updated")


class IgnoreBulkStrategy:
    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome:
        tx.status = "IGNORED"
        return StepOutcome(status="updated")


class ReopenBulkStrategy:
    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome:
        tx.status = "PENDING"
        return StepOutcome(status="updated")


class SetCategoryBulkStrategy:
    def __init__(
        self,
        category_repo: CategoryRepositoryProtocol,
        income_category_repo: IncomeCategoryRepositoryProtocol,
        rule_repo: CategoryRuleRepositoryProtocol,
    ) -> None:
        self._category_repo = category_repo
        self._income_category_repo = income_category_repo
        self._rule_repo = rule_repo

    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome:
        if not req.category:
            return StepOutcome(status="skipped")

        clean_cat = req.category.strip().lower()
        if tx.kind == "EXPENSE" and not await self._category_repo.get_by_key(clean_cat):
            return StepOutcome(status="error", error_message=f"Categoria '{clean_cat}' não existe")
        if tx.kind == "INCOME" and not await self._income_category_repo.get_by_key(clean_cat):
            return StepOutcome(status="error", error_message=f"Categoria '{clean_cat}' não existe")

        tx.category = clean_cat
        if req.remember and tx.merchant:
            await self._rule_repo.upsert_rule(
                pattern=tx.merchant,
                direction=tx.direction,
                kind=tx.kind,
                category=clean_cat,
                source="LEARNED",
            )
        return StepOutcome(status="updated")
```

No `ImportService.bulk_action`, toda a escada `if/elif/else` de 65 linhas é substituída por uma busca $O(1)$ no dicionário de estratégias:

```python
strategy = self._bulk_strategies.get(req.action)
if strategy is None:
    errors.append(BulkActionError(id=tx_id, error=f"Ação desconhecida: {req.action}"))
    continue
outcome = await strategy.execute(tx, req)
```

---

### 2.2. Strategy para Commit de Transações Aprovadas (`finance_api/services/strategies/commit_strategies.py`)

Criamos o contrato `TransactionCommitStrategy` e 3 estratégias concretas mapeadas por `TransactionKind`:

- **`ExpenseCommitStrategy`**: Valida `tx.category`, cria `SpentCreate`, chama `spent_service.create(...)` e preenche `tx.committed_spent_id`.
- **`IncomeCommitStrategy`**: Valida `tx.category`, cria `IncomeCreate`, chama `income_service.create(...)` e preenche `tx.committed_income_id`.
- **`NonRecordCommitStrategy`**: Usada para `TRANSFER`, `INVOICE_PAYMENT` e `REFUND`; apenas marca `tx.status = "COMMITTED"` e incrementa `processed_without_record`.

```python
commit_strategies: dict[str, TransactionCommitStrategy] = {
    "EXPENSE": ExpenseCommitStrategy(spent_service),
    "INCOME": IncomeCommitStrategy(income_service),
    "TRANSFER": NonRecordCommitStrategy(),
    "INVOICE_PAYMENT": NonRecordCommitStrategy(),
    "REFUND": NonRecordCommitStrategy(),
}
```

---

### 2.3. Strategy para Construção de Gráficos (`graph_api/services/chart_strategies.py`)

Na `graph_api`, separamos o **algoritmo de construção da figura (`go.Figure`)** da **renderização em imagem (`fig.to_image`)**:

```python
from enum import StrEnum
from typing import Any, Protocol

import plotly.express as px
import plotly.graph_objects as go


class ChartMode(StrEnum):
    SALDO = "saldo"
    LIMITES = "limites"
    PIE = "pie"


class ChartBuildStrategy(Protocol):
    def build_figure(self, balances: list[dict[str, Any]], title: str) -> go.Figure:
        ...


class LimitsBarChartStrategy:
    def build_figure(self, balances: list[dict[str, Any]], title: str) -> go.Figure:
        categories = [b["category_display_name"] for b in balances]
        limits = [b["limit"] for b in balances]
        fig = go.Figure(
            data=[
                go.Bar(
                    name="Limite",
                    x=categories,
                    y=limits,
                    marker_color="cornflowerblue",
                    text=[f"R$ {v:.2f}" for v in limits],
                    textposition="auto",
                )
            ]
        )
        fig.update_layout(
            title=title,
            yaxis_title="Valor (R$)",
            xaxis_title="Categoria",
            template="plotly_white",
        )
        return fig


class BalanceStackedBarChartStrategy:
    def build_figure(self, balances: list[dict[str, Any]], title: str) -> go.Figure:
        ...


class ExpensePieChartStrategy:
    def build_figure(self, balances: list[dict[str, Any]], title: str) -> go.Figure:
        ...
```

E o `GraphRendererService` (Context) recebe o registro `dict[ChartMode, ChartBuildStrategy]` via construtor e executa a conversão `fig.to_image(format="png", width=800, height=500)` em um único ponto centralizado!

---

## 3. Checklist de Execução e Testes (Fase 3)

- [ ] Criar `finance_api/services/strategies/bulk_actions.py` com `BulkActionStrategy` (`Protocol`) e as 4 estratégias concretas.
- [ ] Criar `finance_api/services/strategies/commit_strategies.py` com `TransactionCommitStrategy` (`Protocol`) e as 3 estratégias concretas.
- [ ] Refatorar `ImportService.bulk_action` e `ImportService.commit_approved` para usar os dicionários de estratégia injetados.
- [ ] Criar `graph_api/services/chart_strategies.py` e `GraphRendererService` injetado via `Annotated[..., Depends(...)]` no router `graph_api/routers/graphs.py`.
- [ ] Executar suíte de testes de `finance_api` e `graph_api` (`uv run pytest`).
