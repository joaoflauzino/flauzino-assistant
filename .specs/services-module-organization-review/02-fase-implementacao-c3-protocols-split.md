# Fase de Implementação — Split de `protocols.py` (C3) + Regra F do Gate

> **Origem:** [01-diagnostico-inventario-e-decisoes.md](./01-diagnostico-inventario-e-decisoes.md) — decisão humana **A**
> **Status:** 🟨 Proposta de implementação — **aguarda aprovação explícita** (nenhum código foi alterado)
> **Escopo:** `finance_api/services/protocols.py` (split por domínio) + `tests/architecture/test_module_organization.py` (Regra F)
> **Natureza:** movimentação pura de símbolos. **Zero mudança de comportamento, assinatura pública ou contrato HTTP.**
> **Candidatos recusados nesta fase:** C1, C2, C4, C5, C6 permanecem planos (nada a fazer).
>
> **Execução:** ✅ T1–T7 concluídas em 2026-11-02 — ver §13. Diff pronto para revisão; **commit/push pendentes de autorização**.

---

## 1. Contexto e decisão

A decisão A aceitou o diagnóstico: **nenhum pacote novo** e **apenas o C3** entra em implementação. O defeito objetivo que justifica a fase:

| # | Defeito | Evidência (medida) |
|---|---|---|
| D1 | `finance_api/services/protocols.py` é um *contract bag* de 4 features | 13 contratos + 2 type aliases, 169 LOC, 15 consumidores de produção |
| D2 | Contrato + implementação no mesmo arquivo | `BaseClassificationHandler` é `ABC` **com fallback implementado**; 8 subclasses vivem em `classification_chain.py` (viola Regra 2) |
| D3 | Helper puro arrasta infraestrutura | `services/utils.py` → `protocols.py` → `httpx`, `models.*`, `repositories.*` (cadeia de import verificada) |

**Objetivo da fase:** cada contrato no seu módulo de domínio, `protocols.py` residual sem infraestrutura, e um gate (Regra F) que impede a regressão. Nenhuma movimentação altera quem consome o quê: só o caminho de import muda.

---

## 2. Escopo

### 2.1 Dentro do escopo

- Criar 5 módulos de contrato (flat, sem pacote novo):
  `services/imports/protocols.py`, `services/classification_protocols.py`, `services/ai_classifier_protocols.py`, `services/lookup_protocols.py`, `services/update_preparation_protocols.py`.
- Mover `BaseClassificationHandler` para `services/classification_chain.py` (onde estão as subclasses).
- Reduzir `services/protocols.py` a contratos transversais (`CategorizedAmountProtocol`).
- Atualizar imports de produção e de teste (12 arquivos de produção + 3 de teste).
- Implementar a **Regra F** no gate + 2 testes sintéticos + legenda/docstring.

### 2.2 Fora do escopo

- Qualquer pacote novo (`imports/` e `tools/` continuam como estão; nenhum `classification/`, `payment/`, `media/`, `clients/`).
- Renomes cosméticos (`tools/graph.py → chart.py`) e candidatos C1/C2/C4/C5/C6.
- Reescrita de assinaturas, `except`, DI, `spents.py`/`incomes.py` instanciando `PaymentResolutionService(db=repo.db)` (achado A5 do relatório).
- Substituir os `*LookupProtocol` pelos repositories concretos (mudaria contratos, não é movimentação).
- Alterar limiares da Regra 8, baseline do gate ou qualquer regra existente (A–E).
- Commit/push (exigem autorização explícita — `AGENTS.md` §7).

---

## 3. Estado atual (mapa símbolo → consumidores)

Contratos existentes em `finance_api/services/protocols.py` e seus consumidores **de produção** (linhas do estado atual):

| Símbolo | Consumidores de produção | Consumidores de teste |
|---|---|---|
| `BulkActionStrategy` | `imports/bulk.py:14`, `imports/bulk_strategies.py:8`, `imports/wiring.py:25` | — |
| `TransactionCommitStrategy` | `imports/commit.py:19`, `imports/commit_strategies.py:14`, `imports/factory.py:28`, `imports/wiring.py:27` | — |
| `DuplicateDetectorStrategy` | `imports/commit_strategies.py:14`, `imports/staging.py:11`, `imports/wiring.py:26` | — |
| `MerchantExtractorStep` | `extractors.py:6` | — |
| `MerchantExtractorPipeline` | `extractors.py:6`, `classification.py:22` | — |
| `ClassificationHandlerProtocol` | `classification.py:21`, `classification_chain.py:18` | — |
| `BaseClassificationHandler` (ABC + fallback) | `classification_chain.py:17` (e 8 subclasses no mesmo arquivo) | `test_classification_chain.py:26`, `test_classification_service.py:17` |
| `AIClassifierHttpClientProtocol` | `ai_classifier.py:7` | — |
| `CategoryLookupProtocol` | `update_preparation.py:16`, `imports/bulk_strategies.py:9` | `imports/test_bulk_strategies.py:23` |
| `IncomeCategoryLookupProtocol` | `update_preparation.py:17`, `imports/bulk_strategies.py:10` | `imports/test_bulk_strategies.py:24` |
| `PaymentMethodLookupProtocol` | `update_preparation.py:18` | — |
| `PaymentResolutionServiceProtocol` | `update_preparation.py:19` | — |
| `PaymentTargetPayload` | `update_preparation.py:20` | — |
| `UpdatePreparationStep[T]` | `update_preparation.py:21` | — |
| `CategorizedAmountProtocol` | `utils.py:7` | — |

Imports de topo que **saem** do `protocols.py` com o split: `abc`, `datetime.date`, `decimal.Decimal`, `uuid.UUID`, `Callable`, `Any`, `httpx`, `models/{categories,income_categories,payment_methods,staged_transactions}`, `repositories/staged_transactions`, `schemas/{classification,imports,payment_resolution}`.

---

## 4. Estrutura-alvo

```text
finance_api/services/
├── protocols.py                     # transversal: CategorizedAmountProtocol (sem infra)
├── classification_protocols.py      # NOVO: aliases de extrator + ClassificationHandlerProtocol
├── ai_classifier_protocols.py       # NOVO: AIClassifierHttpClientProtocol
├── lookup_protocols.py              # NOVO: *LookupProtocol (compartilhados por 2 features)
├── update_preparation_protocols.py  # NOVO: UpdatePreparationStep, PaymentTargetPayload,
│                                    #       PaymentResolutionServiceProtocol
├── classification_chain.py          # + BaseClassificationHandler (ABC + fallback)
└── imports/
    └── protocols.py                 # NOVO: BulkAction, TransactionCommit, DuplicateDetector
```

**Por que flat e não pacote:** todos os grupos ficam abaixo do gatilho da Regra 8 (por exemplo, `classification*` = 3 arquivos / ~420 LOC; `payment*` = 3/211; `update*` = 2/~200). Criar pacote aqui seria decisão estética, recusada no diagnóstico.

**Convenção que a fase estabelece** (a registrar na doc, T7): com módulos flat, o equivalente a `"<domínio>/protocols.py"` é `"<domínio>_protocols.py"` no mesmo diretório. Contratos compartilhados por **mais de uma feature** ficam em um módulo nomeado pela capacidade (`lookup_protocols.py`), nunca no `protocols.py` transversal.

---

## 5. Conteúdo dos novos módulos

> Todos: imports absolutos, blocos PEP 8, `__all__` proibido, sem re-export, sem alias de compatibilidade.

### 5.1 `finance_api/services/imports/protocols.py` (novo)

```python
"""Structural contracts for the import feature (bulk actions, commit, duplicates)."""

from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.schemas.imports import (
    BulkActionRequest,
    CommitContext,
    CommitStepOutcome,
    StepOutcome,
)


class BulkActionStrategy(Protocol):
    """Structural contract for executing a bulk action on a StagedTransaction."""

    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome: ...


class TransactionCommitStrategy(Protocol):
    """Structural contract for committing an approved StagedTransaction."""

    async def commit(
        self,
        tx: StagedTransaction,
        ctx: CommitContext,
    ) -> CommitStepOutcome: ...


class DuplicateDetectorStrategy(Protocol):
    """Structural contract for detecting possible duplicates of a staged row."""

    async def detect(
        self,
        tx_repo: StagedTransactionRepository,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        amount: Decimal,
        tx_date: date,
    ) -> tuple[UUID | None, UUID | None]: ...
```

### 5.2 `finance_api/services/classification_protocols.py` (novo)

```python
"""Structural contracts for the transaction classification domain."""

from collections.abc import Callable
from typing import Protocol

from finance_api.schemas.classification import (
    ClassificationContext,
    ClassificationResult,
    ExtractedMerchantInfo,
    RawTransactionText,
)

type MerchantExtractorStep = Callable[[RawTransactionText], ExtractedMerchantInfo | None]
type MerchantExtractorPipeline = Callable[[RawTransactionText], ExtractedMerchantInfo]


class ClassificationHandlerProtocol(Protocol):
    """Structural contract for handlers in the transaction classification chain."""

    def set_next(
        self,
        handler: "ClassificationHandlerProtocol",
    ) -> "ClassificationHandlerProtocol": ...

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult: ...
```

### 5.3 `finance_api/services/ai_classifier_protocols.py` (novo)

```python
"""HTTP contract required by the AI classification client."""

from typing import Any, Protocol

import httpx


class AIClassifierHttpClientProtocol(Protocol):
    """HTTP contract required by the AI classification client."""

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        timeout: float,
    ) -> httpx.Response: ...
```

### 5.4 `finance_api/services/lookup_protocols.py` (novo)

```python
"""Structural contracts for lookup-by-key repository capabilities."""

from typing import Protocol

from finance_api.models.categories import Category
from finance_api.models.income_categories import IncomeCategory
from finance_api.models.payment_methods import PaymentMethod


class CategoryLookupProtocol(Protocol):
    """Structural contract for looking up expense categories by key."""

    async def get_by_key(self, key: str) -> Category | None: ...


class IncomeCategoryLookupProtocol(Protocol):
    """Structural contract for looking up income categories by key."""

    async def get_by_key(self, key: str) -> IncomeCategory | None: ...


class PaymentMethodLookupProtocol(Protocol):
    """Structural contract for looking up payment methods by key."""

    async def get_by_key(self, key: str) -> PaymentMethod | None: ...
```

### 5.5 `finance_api/services/update_preparation_protocols.py` (novo)

```python
"""Structural contracts for the shared update-preparation steps."""

from typing import Protocol
from uuid import UUID

from finance_api.schemas.payment_resolution import ResolvedPaymentTarget


class PaymentResolutionServiceProtocol(Protocol):
    """Structural contract for resolving account/credit card relations."""

    async def resolve(
        self,
        payment_method_key: str | None,
        requested_payment_type: str | None = None,
        is_credit_card_hint: bool = False,
    ) -> ResolvedPaymentTarget: ...


class PaymentTargetPayload(Protocol):
    """Update payload that can receive the resolved payment relations."""

    payment_method: str | None
    payment_type: str | None
    account_id: UUID | None
    credit_card_id: UUID | None


class UpdatePreparationStep[T](Protocol):
    """Structural contract for a single preparation step of an update payload."""

    async def prepare(self, data: T) -> None: ...
```

### 5.6 `finance_api/services/protocols.py` (residual, reescrito)

```python
"""Cross-cutting structural contracts shared by finance_api services.

Feature-scoped contracts live next to their domain (``*_protocols.py`` or the
feature package). This module must stay free of infrastructure imports.
"""

from typing import Protocol


class CategorizedAmountProtocol(Protocol):
    """Structural contract for any amount that can be aggregated by category."""

    amount: float
    category: str
```

### 5.7 `finance_api/services/classification_chain.py` (recebe a ABC)

Bloco movido **sem alteração de corpo**, posicionado após os imports e antes de `OwnTransferHandler`:

```python
class BaseClassificationHandler(ABC):
    """Abstract base class providing fluent chaining and default fallback."""

    def __init__(self) -> None:
        self._next_handler: ClassificationHandlerProtocol | None = None

    def set_next(
        self,
        handler: ClassificationHandlerProtocol,
    ) -> ClassificationHandlerProtocol:
        self._next_handler = handler
        return handler

    @abstractmethod
    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if self._next_handler is not None:
            return await self._next_handler.handle(ctx)
        # Fallback final se nenhum handler classificar a categoria (aguarda IA em lote)
        return ClassificationResult(
            merchant=ctx.merchant,
            kind=ctx.default_kind,
            payment_type=ctx.default_payment_type,
            suggested_category=None,
            suggestion_source=None,
            confidence=None,
            description=ctx.description,
            location=ctx.location,
        )
```

Ajuste de imports no arquivo: adicionar `from abc import ABC, abstractmethod`; trocar o import de `protocols` por `from finance_api.services.classification_protocols import ClassificationHandlerProtocol`. Arquivo passa de 220 para ~248 LOC (limite do gate: 300).

---

## 6. Tabela de edições

### 6.1 Produção

| Arquivo | Linha atual | De | Para |
|---|---|---|---|
| `services/ai_classifier.py` | 7 | `from finance_api.services.protocols import AIClassifierHttpClientProtocol` | `from finance_api.services.ai_classifier_protocols import AIClassifierHttpClientProtocol` |
| `services/classification.py` | 20-23 | `from finance_api.services.protocols import (ClassificationHandlerProtocol, MerchantExtractorPipeline)` | `from finance_api.services.classification_protocols import (ClassificationHandlerProtocol, MerchantExtractorPipeline)` |
| `services/extractors.py` | 6 | `from finance_api.services.protocols import MerchantExtractorPipeline, MerchantExtractorStep` | `from finance_api.services.classification_protocols import MerchantExtractorPipeline, MerchantExtractorStep` |
| `services/classification_chain.py` | 3-19 | importa `BaseClassificationHandler, ClassificationHandlerProtocol` de `protocols` | remove a ABC do import; passa a importar só `ClassificationHandlerProtocol` de `classification_protocols`; adiciona `from abc import ABC, abstractmethod` |
| `services/update_preparation.py` | 15-22 | importa 6 símbolos de `protocols` | dois imports: `lookup_protocols` (3 lookups) e `update_preparation_protocols` (3 restantes) |
| `services/utils.py` | 7 | `from finance_api.services.protocols import CategorizedAmountProtocol` | **sem alteração** (o caminho continua válido) |
| `services/imports/bulk.py` | 14 | `...protocols import BulkActionStrategy` | `from finance_api.services.imports.protocols import BulkActionStrategy` |
| `services/imports/bulk_strategies.py` | 7-11 | importa 3 símbolos (1 de imports, 2 de lookup) | `from finance_api.services.imports.protocols import BulkActionStrategy` + `from finance_api.services.lookup_protocols import CategoryLookupProtocol, IncomeCategoryLookupProtocol` |
| `services/imports/commit.py` | 19 | `...protocols import TransactionCommitStrategy` | `from finance_api.services.imports.protocols import TransactionCommitStrategy` |
| `services/imports/commit_strategies.py` | 14 | `...protocols import DuplicateDetectorStrategy, TransactionCommitStrategy` | `from finance_api.services.imports.protocols import DuplicateDetectorStrategy, TransactionCommitStrategy` |
| `services/imports/factory.py` | 28 | `...protocols import TransactionCommitStrategy` | `from finance_api.services.imports.protocols import TransactionCommitStrategy` |
| `services/imports/staging.py` | 11 | `...protocols import DuplicateDetectorStrategy` | `from finance_api.services.imports.protocols import DuplicateDetectorStrategy` |
| `services/imports/wiring.py` | 24-28 | importa 3 símbolos | `from finance_api.services.imports.protocols import (BulkActionStrategy, DuplicateDetectorStrategy, TransactionCommitStrategy)` |

**Total:** 12 arquivos de produção editados, 5 criados, 1 reescrito (residual), 1 recebe bloco movido.

### 6.2 Testes

| Arquivo | Linha | De | Para |
|---|---|---|---|
| `finance_api/tests/services/test_classification_chain.py` | 26 | `from finance_api.services.protocols import BaseClassificationHandler` | `from finance_api.services.classification_chain import BaseClassificationHandler` |
| `finance_api/tests/services/test_classification_service.py` | 17 | idem | idem |
| `finance_api/tests/services/imports/test_bulk_strategies.py` | 22-25 | importa 2 lookups de `protocols` | `from finance_api.services.lookup_protocols import (CategoryLookupProtocol, IncomeCategoryLookupProtocol)` |

Nenhum patch target muda: os alvos de `mocker.patch(...)` estão em `services.spents`, `services.incomes`, `services.limits`, `agent_api.services.agent`, `agent_api.services.ocr` e routers — todos intocados.

### 6.3 Ordem dos imports (PEP 8)

Em `imports/bulk_strategies.py` e `update_preparation.py` o bloco local ganha dois imports absolutos; manter ordem alfabética dentro do bloco (`finance_api.services.imports.protocols` antes de `finance_api.services.lookup_protocols`, que vem antes de `finance_api.services.update_preparation_protocols`). `ruff` valida (`I001`).

---

## 7. Regra F — pureza de contratos e helpers

### 7.1 Definição normativa

> **Regra F:** os módulos de contrato transversal (`services/protocols.py`) e de helpers puros (`services/utils.py`) **não podem** importar `httpx`, `*.models.*` ou `*.repositories.*`.

Justificativa: é exatamente o defeito D3. Contratos de feature (dentro de pacote, como `imports/protocols.py`) ficam isentos de propósito — eles referenciam o modelo do seu domínio por assinatura, e o pacote é a fronteira.

### 7.2 Implementação em `tests/architecture/test_module_organization.py`

Acréscimos (AST, sem dependência nova — `ast` é stdlib):

```python
import ast

DEFINITION_MODULE_STEMS = frozenset({"protocols", "utils"})
INFRASTRUCTURE_MODULE_PARTS = frozenset({"models", "repositories"})
INFRASTRUCTURE_ROOTS = frozenset({"httpx"})


def iter_imported_modules(source: str) -> Iterable[str]:
    """Yields every module path imported by a source file."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def imports_infrastructure(module: str) -> bool:
    """Checks whether a module path points to infrastructure layers."""
    parts = module.split(".")
    return parts[0] in INFRASTRUCTURE_ROOTS or bool(INFRASTRUCTURE_MODULE_PARTS & set(parts))


def collect_definition_purity_violations(paths: Sequence[pathlib.Path]) -> dict[str, str]:
    """Rule F: cross-cutting contracts and pure helpers must not import infrastructure."""
    violations: dict[str, str] = {}
    for path in paths:
        is_transversal = path.parent.name == "services" and path.stem in DEFINITION_MODULE_STEMS
        if not is_transversal:
            continue
        for module in iter_imported_modules(path.read_text(encoding="utf-8")):
            if imports_infrastructure(module):
                violations[f"F|{path.as_posix()}|{module}"] = (
                    f"contrato/helper transversal importa infraestrutura '{module}'"
                )
    return violations
```

Integração em `collect_violations` (após a Regra E) e atualização de:

- docstring do módulo (lista de A–E → A–F);
- `RULE_LEGEND` → acrescentar `F=contrato/helper transversal importa models/repositories/httpx`.

### 7.3 Testes sintéticos (2 novos)

```python
def test_definition_purity_rule_flags_infrastructure_import(tmp_path: pathlib.Path) -> None:
    module = write_module(
        tmp_path / "services" / "protocols.py",
        "from finance_api.models.spents import Spent\n",
    )

    keys = collect_violations([tmp_path])

    assert f"F|{module.as_posix()}|finance_api.models.spents" in keys


def test_definition_purity_rule_allows_schema_imports(tmp_path: pathlib.Path) -> None:
    write_module(
        tmp_path / "services" / "protocols.py",
        "from finance_api.schemas.spents import SpentCreate\n",
    )

    assert not [key for key in collect_violations([tmp_path]) if key.startswith("F|")]
```

Resultado esperado do arquivo de gate: **7 → 9 testes**, todos verdes.

### 7.4 Verificação de que a Regra F é satisfazível hoje

| Arquivo alvo da Regra F | Após o split |
|---|---|
| `finance_api/services/protocols.py` | importa só `typing` ✅ |
| `finance_api/services/utils.py` | `schemas` + `services.protocols` ✅ |
| `agent_api/services/protocols.py` | só `agent_api.schemas` ✅ |
| `agent_api/services/utils.py` | só `agent_api.schemas` ✅ |
| `graph_api/services/protocols.py` | `typing` + `plotly` (não é infraestrutura listada) ✅ |
| `telegram_api` | não possui `services/protocols.py` nem `services/utils.py` ✅ |

Sem baseline e sem allowlist: a regra entra já estrita.

---

## 8. Tarefas (uma unidade por commit, todas behavior-free)

| # | Tarefa | Arquivos | Gate de saída |
|---|---|---|---|
| T1 | Contratos de importação → `imports/protocols.py` | cria `imports/protocols.py`; remove 3 símbolos de `protocols.py`; edita `bulk`, `bulk_strategies`, `commit`, `commit_strategies`, `factory`, `staging`, `wiring` | `pytest finance_api/tests/services/imports -q` + architecture |
| T2 | Contratos de classificação + ABC para o chain | cria `classification_protocols.py`; move `BaseClassificationHandler`; edita `classification`, `extractors`, `classification_chain`, 2 testes | `pytest finance_api/tests/services/test_classification*.py finance_api/tests/services/test_extractors.py -q` + architecture |
| T3 | Contrato do cliente de IA | cria `ai_classifier_protocols.py`; edita `ai_classifier.py` | `pytest finance_api/tests/services/test_ai_classifier.py -q` |
| T4 | Lookups + preparação de update | cria `lookup_protocols.py` e `update_preparation_protocols.py`; edita `update_preparation`, `imports/bulk_strategies`, 1 teste | `pytest finance_api/tests/services/test_update_preparation.py finance_api/tests/services/imports/test_bulk_strategies.py -q` |
| T5 | Resíduo transversal | reescreve `protocols.py`; confere que só resta `CategorizedAmountProtocol` | `wc -l` ≈ 10; `pytest finance_api/tests/services/test_utils.py -q`; `python -c "import finance_api.main"` |
| T6 | Regra F | edita o gate (função + integração + docstring + legenda) e adiciona 2 testes | `pytest tests/architecture -q` (9 passed) |
| T7 | Documentação | `.specs/services-modules-quality-refactoring/08-estrutura-padrao-apis.md` (convenção `*_protocols.py` + isenção de contratos de feature) e este arquivo (evidências) | revisão humana |

**Regra de ouro por tarefa:** `git mv`/edição pura, sem alias de compatibilidade, sem re-export, sem `__all__`; diff revisável com `git diff -M`.

---

## 9. Comandos de verificação (obrigatórios antes de "concluído")

```bash
# 1. Import dos apps (pega ciclo/erro de import antes de qualquer teste)
uv run python -c "import finance_api.main"
uv run python -c "import agent_api.main"

# 2. Nenhum consumidor deve importar contrato movido do protocols.py raiz
grep -rn "services.protocols import" --include='*.py' finance_api | grep -v __pycache__
# esperado: apenas services/utils.py importando CategorizedAmountProtocol

# 3. Nenhum import residual no protocols.py raiz
grep -n "^from \|^import " finance_api/services/protocols.py
# esperado: somente "from typing import Protocol"

# 4. Gates de qualidade
make format
make lint
uv run pytest tests/architecture -q
uv run pytest finance_api/tests -q
uv run pytest -q                      # suíte completa (baseline: 703 passed)

# 5. Movimentação pura
git diff -M --stat
```

---

## 10. Riscos e mitigação

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Esquecer um consumidor → `ImportError` só em runtime | Baixa | Alto | passo 1 e 2 do §9 + suíte completa |
| Ciclo de import ao mover a ABC para `classification_chain.py` | Baixa | Alto | `classification_protocols` só importa `schemas`; validar com `import finance_api.main` |
| `ruff` acusar ordem de imports (I001) nos arquivos com 2 blocos locais | Média | Baixo | `make format` + `make lint` antes de fechar cada tarefa |
| `classification_chain.py` passar de 300 LOC | Baixa | Médio | 220 + 28 = ~248; `wc -l` no T2 |
| Regra F quebrar em outro módulo não previsto | Baixa | Médio | §7.4 lista todos os alvos; rodar o gate no T6 antes de fechar |
| Regra F exigir allowlist futura | Baixa | Baixo | proibido criar allowedlist nesta fase; se surgir caso legítimo, volta para revisão |
| Perda de histórico no diff | Média | Baixo | edições por bloco + `git diff -M` no fechamento |

---

## 11. Critérios de aceite

- [x] `finance_api/services/protocols.py` contém apenas contratos transversais e **zero** import de `httpx`/`models`/`repositories` (14 LOC, import único: `from typing import Protocol`).
- [x] Nenhum consumidor importa contrato de feature a partir de `services.protocols` (verificação do §9.2: só `utils.py → CategorizedAmountProtocol`).
- [x] Cada contrato mora em módulo coerente com seu domínio, sem `__all__`, sem re-export, sem alias.
- [x] `BaseClassificationHandler` não convive mais com os contratos (Regra 2), e continua sendo o mesmo ABC com o mesmo fallback.
- [x] Assinaturas públicas, contratos HTTP, DI e comportamento **inalterados** (suíte completa verde, nenhum teste alterado além de imports).
- [x] Regra F implementada, integrada, documentada na legenda e coberta por 2 testes sintéticos.
- [x] `tests/architecture` verde (9 testes), `finance_api/tests` verde (409), suíte completa verde (**705 passed**).
- [x] `make format` e `make lint` limpos (`ruff`: All checks passed).
- [x] `git diff -M` mostra apenas movimentação/imports, sem alteração de lógica.
- [x] Nenhum commit/push executado sem autorização explícita.

---

## 12. Rollback

Cada tarefa (T1–T7) é um commit isolado e auto-contido. Rollback = `git revert <sha>` do commit da tarefa, sem dependência de migração de dados, schema ou configuração. Se T6 (Regra F) for revertida isoladamente, o split (T1–T5) permanece válido.

---

## 13. Evidências de execução

| Tarefa | Status | Data | Testes | Observações |
|---|---|---|---|---|
| T1 | ✅ concluída | 2026-11-02 | `finance_api/tests` 409 passed | `imports/protocols.py` criado; 7 consumidores migrados |
| T2 | ✅ concluída | 2026-11-02 | `test_classification*` + `test_extractors` verdes | `classification_protocols.py` criado; ABC movida para `classification_chain.py` (248 LOC) |
| T3 | ✅ concluída | 2026-11-02 | `test_ai_classifier` verde | `ai_classifier_protocols.py` criado; `httpx` saiu do `protocols.py` |
| T4 | ✅ concluída | 2026-11-02 | `test_update_preparation` + `test_bulk_strategies` verdes | `lookup_protocols.py` e `update_preparation_protocols.py` criados |
| T5 | ✅ concluída | 2026-11-02 | `test_utils` verde | `protocols.py` residual: 14 LOC, só `CategorizedAmountProtocol` |
| T6 | ✅ concluída | 2026-11-02 | `tests/architecture` **9 passed** | Regra F + 2 testes sintéticos + legenda/docstring |
| T7 | ✅ concluída | 2026-11-02 | — | Convenção `*_protocols.py`/Regra F registrada em `08-estrutura-padrao-apis.md` §1.4 |

**Verificação final:** `make format` (black: 363 files unchanged) · `make lint` (ruff: All checks passed) · `uv run pytest -q` → **705 passed** · `import finance_api.main`/`agent_api.main` OK.

**Pendente de autorização humana:** `git commit` / `git push` (nenhum executado).
