# Fase 5: Padronização Python 3.13+ & Clean Code (PEP 8, Guard Clauses e Tipagem)

**Skill aplicada:** `python-pep8-guidelines`  
**Serviços-alvo:** `finance_api`, `agent_api`, `graph_api`, `telegram_api`

---

## 1. Diagnóstico Detalhado (Estado Atual)

Ao auditar os arquivos das 4 aplicações Python contra o checklist da skill `python-pep8-guidelines` e da seção 3.4 do `AGENTS.md`, identificamos os seguintes pontos:

1. **Imports de Tipagem Legados (`Optional`, `Union`, `List`, `Dict`, `Sequence` de `typing`)**:
   - Exemplos: `finance_api/routers/imports.py` (`from typing import Optional`), `finance_api/repositories/accounts.py` (`from typing import Optional, Sequence`).
   - Em Python 3.13+, `Optional[T]` deve ser sempre `T | None`, coleções nativas são `list[T]`, `dict[K, V]`, `tuple[T, ...]`, e `Sequence` deve vir de `collections.abc`.
2. **Ordem de Blocos de Imports no Topo**:
   - Exemplo em `finance_api/core/dependencies.py` (linhas 1-9): imports locais (`from finance_api.repositories...`) aparecem **antes** dos imports de terceiros (`from fastapi import Depends`), quebrando a regra dos 3 blocos da PEP 8 (1. Stdlib ➔ 2. Third-party ➔ 3. Local).
   - Exemplo em `agent_api/dependencies.py` (linha 1): `from agent_api.services.classify import ClassifyService` está acima de `import httpx`.
3. **Uso de `float` para Valores Monetários em Schemas e Conversões**:
   - Em `finance_api/services/imports.py` (linhas 380, 646, 671), há conversões `float(tx.amount)` ao alimentar `SpentCreate` / `IncomeCreate` / `StagedTransactionResponse`. Deve-se preservar `Decimal` ponta a ponta na lógica de negócios.
4. **Anotações de Retorno Incompletas em Routers e Funções Auxiliares**:
   - Endpoints em `finance_api/routers/imports.py` e funções internas como `post_init` / `shutdown` em `telegram_api/main.py` não declaram tipo de retorno explícito (`-> ImportBatchResponse`, `-> None`).
5. **Decomposição por Responsabilidade Única (SRP)**:
   - `ImportService.create_batch_from_upload` (linhas 109-356, ~247 linhas em um único método!) faz: detecção de parser, resolução de conta/cartão, cálculo de SHA-256, cálculo de fingerprints, criação de lote, classificação de cada item, detecção de duplicata manual, cálculo de data de competência de salário, chamada de IA em lote e persistência.
   - Com as Fases 2, 3 e 4 mais a decomposição em métodos auxiliares coesos (`_build_staged_transactions`, `_enrich_with_batch_ai`, `_compute_competence_date`), cada método ficará enxuto (< 35 linhas) e com no máximo 3 condicionais.

---

## 2. Regras de Padronização (Exemplos Antes vs. Depois)

### 2.1. Organização Estrita de Imports em 3 Blocos e Tipagem 3.13+

```python
# ❌ ANTES (finance_api/routers/imports.py)
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from finance_api.core.dependencies import get_category_rule_repository, get_import_service

@router.post("/", response_model=ImportBatchResponse, status_code=status.HTTP_201_CREATED)
async def upload_statement(
    file: UploadFile = File(..., description="Arquivo de extrato (CSV)"),
    account_id: Optional[UUID] = Form(None, description="ID da conta bancária"),
    credit_card_id: Optional[UUID] = Form(None, description="ID do cartão de crédito"),
    service: ImportService = Depends(get_import_service),
):
    ...
```

```python
# ✅ DEPOIS (Python 3.13+ & PEP 8 Strict)
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from finance_api.core.dependencies import ImportServiceDep
from finance_api.core.exceptions import ValidationError
from finance_api.schemas.imports import ImportBatchResponse


@router.post("/", response_model=ImportBatchResponse, status_code=status.HTTP_201_CREATED)
async def upload_statement(
    service: ImportServiceDep,
    file: UploadFile = File(..., description="Arquivo de extrato (CSV)"),
    account_id: UUID | None = Form(None, description="ID da conta bancária"),
    credit_card_id: UUID | None = Form(None, description="ID do cartão de crédito"),
) -> ImportBatchResponse:
    """Realiza o upload de um arquivo de extrato bancário para staging."""
    content = await file.read()
    if not content:
        raise ValidationError("Arquivo vazio.")
    return await service.create_batch_from_upload(
        file_bytes=content,
        filename=file.filename or "extrato.csv",
        account_id=account_id,
        credit_card_id=credit_card_id,
    )
```

### 2.2. Guard Clauses e Funções Coesas (SRP) no `ImportService`

Extrair o cálculo de data de competência (linhas 236-258 de `finance_api/services/imports.py`) para uma função pura com *Guard Clauses*:

```python
SALARY_KEYWORDS: tuple[str, ...] = (
    "SALARIO",
    "SALÁRIO",
    "FOLHA",
    "PRO-LABORE",
    "REMUNERACAO",
    "VENCIMENTO",
    "PPR",
    "PLR",
)


def compute_income_competence_date(
    kind: str,
    occurred_date: date,
    raw_title: str,
    raw_description: str | None,
) -> date | None:
    """Calcula a data de competência para receitas (salários até o 5º dia útil contam no mês anterior)."""
    if kind != "INCOME":
        return None

    norm_raw = f"{raw_title} {raw_description or ''}".upper()
    is_salary_like = any(keyword in norm_raw for keyword in SALARY_KEYWORDS)
    if is_salary_like and occurred_date.day <= 7:
        return occurred_date.replace(day=1) - timedelta(days=1)

    return occurred_date
```

---

## 3. Checklist de Auditoria PEP 8 & Python 3.13+ (Quality Gates)

- [ ] **Zero `Optional` / `Union` / `List` / `Dict` de `typing`**: Substituir em todos os arquivos de `finance_api`, `agent_api`, `graph_api` e `telegram_api` por `T | None`, `list[T]`, `dict[K, V]`.
- [ ] **Imports em 3 blocos no topo**: Garantir que todos os arquivos tenham `1. Stdlib`, `2. Third-party`, `3. Local` separados por 1 linha em branco, validados com `ruff check --select I`.
- [ ] **Tipagem 100% explícita**: Adicionar `-> ReturnType` (incluindo `-> None`) em todos os endpoints, métodos de serviço/repositório e handlers do Telegram.
- [ ] **Decomposição de métodos longos**: Quebrar `ImportService.create_batch_from_upload` e `AgentService.get_response` em métodos privados coesos com responsabilidade única.
- [ ] **Validação Final Automatizada**:
  - `make format`
  - `make lint`
  - `uv run pytest`
