# Fase 2: Chain of Responsibility no Motor de Classificação e Extração

**Skill aplicada:** `python-pattern-chain-of-responsibility`  
**Serviço-alvo:** `finance_api` (`finance_api/services/classification.py` e `finance_api/services/imports.py`)

---

## 1. Diagnóstico Detalhado (Estado Atual)

Em `finance_api/services/classification.py`, existiam **dois grandes blocos de condicionais sequenciais (`if`)** que violavam o limite máximo de 3 condicionais por função (`AGENTS.md` seção 3.4) e o Princípio da Responsabilidade Única (SRP):

1. **`extract_merchant_location_desc`** (linhas 67-123):
   - Avalia sequencialmente **7 regras diferentes** de extração de texto (Pagamento de fatura, Anuidade, Estorno, Cartão `PAYGO*`, Pix enviado, Pix recebido, Devolução Pix, Salário/PPR e Fallback).
2. **`classify_transaction`** (linhas 125-299):
   - Avalia sequencialmente **9 etapas de classificação**:
     1. Transferência entre contas próprias (`is_own_transfer`)
     2. Pagamento de fatura de cartão (`INCLUSAO DE PAGAMENTO`, `PGTO FAT CARTAO`, etc.)
     3. Estorno / Reembolso (`DEVOL RECEBIDA PIX`, `ESTORNO`)
     4. Anuidade do Cartão (`ANUIDADE`)
     5. Salário (`CRED SALARIO`, `ADTO SALARIO`)
     6. PPR / PLR (`PPR`, `PLR`)
     7. Pix recebido de terceiros (`PIX RECEBIDO`, `TRANSF RECEBIDA`)
     8. Memória de comerciantes no banco (`self.rule_repo.find_matching_rule`)
     9. Categoria fornecida pelo banco (`BANK_CATEGORY_MAP`)
     10. Fallback sem categoria (que depois passa pela IA em lote dentro de `ImportService`).

---

## 2. Solução Proposta (Python 3.13+ Idiomático)

Aplicaremos as **duas variantes** da skill `python-pattern-chain-of-responsibility`:

1. **Variante Funcional Leve (`Callable` + `type` PEP 695)** para a extração síncrona e pura de `merchant`, `location` e `description`.
2. **Variante Orientada a Objetos (`AsyncHandlerProtocol[T]` + `BaseAsyncHandler[T]`)** para o pipeline assíncrono de classificação de transações (pois alguns handlers são em memória e outros consultam o banco de dados via `CategoryRuleRepository`).

---

### 2.1. Pipeline Funcional de Extração de Merchant (`finance_api/services/extractors.py`)

Como os extratores de texto são funções puras e síncronas (`stateless`), usamos a variante funcional da skill:

```python
from collections.abc import Callable
from dataclasses import dataclass
import re

from finance_api.services.classification import _normalize


@dataclass(frozen=True)
class RawTransactionText:
    title: str
    description: str
    norm_title: str
    direction: str


@dataclass(frozen=True)
class ExtractedMerchantInfo:
    merchant: str
    location: str | None
    short_description: str


type MerchantExtractorStep = Callable[[RawTransactionText], ExtractedMerchantInfo | None]


def extract_card_fees_and_invoice(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    if "INCLUSAO DE PAGAMENTO" in raw.norm_title or "PGTO FAT CARTAO" in raw.norm_title:
        return ExtractedMerchantInfo("C6 BANK", None, "Pagamento de Fatura")
    if "ANUIDADE" in raw.norm_title:
        return ExtractedMerchantInfo("C6 BANK", None, "Anuidade Cartão")
    if "ESTORNO" in raw.norm_title:
        return ExtractedMerchantInfo("C6 BANK", None, "Estorno Tarifa")
    return None


def extract_paygo_card(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    if not raw.description or ("PAYGO*" not in raw.description and "CARTAO" not in raw.norm_title):
        return None

    match_city = re.search(
        r"PAYGO\*([^\s]+(?:\s+[^\s]+)*?)\s{2,}([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+)*?)\s+BRA",
        raw.description,
    )
    if match_city:
        merchant = match_city.group(1).strip()
        location = match_city.group(2).strip()
        short_desc = raw.title if len(raw.title) <= 50 else merchant[:50]
        return ExtractedMerchantInfo(merchant, location, short_desc)

    match_fallback = re.search(r"PAYGO\*([^.]+?)(?:\s{2,}|\.|$)", raw.description)
    if match_fallback:
        merchant = match_fallback.group(1).strip()
        short_desc = raw.title if len(raw.title) <= 50 else merchant[:50]
        return ExtractedMerchantInfo(merchant, "Uberlândia", short_desc)

    return None


def extract_pix_sent(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    match = re.search(r"Pix enviado para\s+(.+)", raw.title, re.IGNORECASE)
    if not match:
        return None
    merchant = match.group(1).strip()
    return ExtractedMerchantInfo(merchant, None, f"Pix {merchant}"[:50])


def extract_pix_received(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    match = re.search(r"Pix recebido de\s+(.+)", raw.title, re.IGNORECASE)
    if not match:
        return None
    merchant = match.group(1).strip()
    return ExtractedMerchantInfo(merchant, None, f"Pix de {merchant}"[:50])


def extract_pix_refund(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    match = re.search(r"Devol recebida pix(?: de)?\s*(.+)?", raw.title, re.IGNORECASE)
    if not match or not match.group(1):
        return None
    merchant = match.group(1).strip()
    return ExtractedMerchantInfo(merchant, None, raw.title[:50])


def extract_salary_or_bonus(raw: RawTransactionText) -> ExtractedMerchantInfo | None:
    keywords = ("CRED SALARIO", "ADTO SALARIO", "PAGAMENTO PPR", "PLR")
    if any(k in raw.norm_title for k in keywords):
        return ExtractedMerchantInfo("C6 BANK", None, raw.title[:50])
    return None


def build_extractor_pipeline(*steps: MerchantExtractorStep) -> Callable[[RawTransactionText], ExtractedMerchantInfo]:
    """Compõe os passos de extração em uma cadeia com short-circuit e fallback padrão."""

    def run(raw: RawTransactionText) -> ExtractedMerchantInfo:
        for step in steps:
            result = step(raw)
            if result is not None:
                return result
        merchant = raw.title or raw.description or "Transação"
        short_desc = raw.title[:50] if raw.title else "Transação"
        return ExtractedMerchantInfo(merchant, None, short_desc)

    return run
```

---

### 2.2. Cadeia de Responsabilidade para Classificação (`finance_api/services/classification_chain.py`)

Seguindo a skill `python-pattern-chain-of-responsibility`, criamos o `ClassificationContext` imutável, o contrato estrutural `ClassificationHandlerProtocol[T, R]` e a classe base `BaseClassificationHandler`:

```mermaid
flowchart LR
    Ctx[ClassificationContext] --> H1[OwnTransferHandler]
    H1 -- "Não bateu" --> H2[InvoicePaymentHandler]
    H2 -- "Não bateu" --> H3[RefundHandler]
    H3 -- "Não bateu" --> H4[CardFeeHandler]
    H4 -- "Não bateu" --> H5[SalaryAndBonusHandler]
    H5 -- "Não bateu" --> H6[InboundPixHandler]
    H6 -- "Não bateu (Vai ao DB)" --> H7[RuleMemoryHandler]
    H7 -- "Não bateu" --> H8[BankCategoryHandler]
    H8 -- "Fallback" --> Def[UnclassifiedDefaultResult]
```

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from finance_api.repositories.category_rules import CategoryRuleRepositoryProtocol
from finance_api.services.classification import BANK_CATEGORY_MAP, ClassificationResult, _normalize


@dataclass(frozen=True)
class ClassificationContext:
    raw_title: str
    raw_description: str | None
    norm_title: str
    norm_desc: str
    norm_combined: str
    direction: str
    amount: Decimal
    merchant: str
    location: str | None
    description: str
    default_kind: str
    default_payment_type: str
    bank_category: str | None = None
    is_credit_card: bool = False


# ---------------------------------------------------------------------------
# 1. Handler Interface (Protocol - Structural Contract)
# ---------------------------------------------------------------------------
class ClassificationHandlerProtocol(Protocol):
    def set_next(
        self,
        handler: "ClassificationHandlerProtocol",
    ) -> "ClassificationHandlerProtocol":
        ...

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        ...


# ---------------------------------------------------------------------------
# 2. Abstract Base Handler (Encadeamento Fluente + Fallback Padrão)
# ---------------------------------------------------------------------------
class BaseClassificationHandler(ABC):
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


# ---------------------------------------------------------------------------
# 3. Concrete Handlers (Ordenados do mais barato em memória ao mais custoso)
# ---------------------------------------------------------------------------
class OwnTransferHandler(BaseClassificationHandler):
    def __init__(self, holder_names: list[str]) -> None:
        super().__init__()
        self._holder_names = holder_names

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if any(name and name in ctx.norm_combined for name in self._holder_names):
            return ClassificationResult(
                merchant=ctx.merchant,
                kind="TRANSFER",
                payment_type="PIX" if "PIX" in ctx.norm_combined else "TRANSFER",
                suggested_category=None,
                suggestion_source="RULE",
                confidence=Decimal("1.000"),
                description=ctx.description,
                location=ctx.location,
            )
        return await super().handle(ctx)


class InvoicePaymentHandler(BaseClassificationHandler):
    PATTERNS = (
        "INCLUSAO DE PAGAMENTO",
        "PGTO FAT CARTAO",
        "FATURA DE CARTAO",
        "NU PAGAMENTOS",
        "BRADESCARD",
    )

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if any(pat in ctx.norm_combined for pat in self.PATTERNS):
            return ClassificationResult(
                merchant="C6 BANK",
                kind="INVOICE_PAYMENT",
                payment_type="CREDIT" if ctx.is_credit_card else "DEBIT",
                suggested_category=None,
                suggestion_source="RULE",
                confidence=Decimal("1.000"),
                description=ctx.description,
                location=ctx.location,
            )
        return await super().handle(ctx)


class RefundHandler(BaseClassificationHandler):
    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if "DEVOL RECEBIDA PIX" in ctx.norm_title or "ESTORNO" in ctx.norm_combined:
            return ClassificationResult(
                merchant=ctx.merchant,
                kind="REFUND",
                payment_type="CREDIT" if ctx.is_credit_card else "PIX",
                suggested_category=None,
                suggestion_source="RULE",
                confidence=Decimal("0.950"),
                description=ctx.description,
                location=ctx.location,
            )
        return await super().handle(ctx)


class RuleMemoryHandler(BaseClassificationHandler):
    """Camada 2: Consulta ao banco de regras aprendidas (category_rules)."""

    def __init__(self, rule_repo: CategoryRuleRepositoryProtocol) -> None:
        super().__init__()
        self._rule_repo = rule_repo

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        matched_rule = await self._rule_repo.find_matching_rule(ctx.merchant, ctx.direction)
        if matched_rule and matched_rule.category:
            await self._rule_repo.increment_hits(matched_rule.id)
            source = "RULE" if matched_rule.source == "SEED" else "MEMORY"
            conf = Decimal("0.950") if matched_rule.hits >= 2 else Decimal("0.850")
            return ClassificationResult(
                merchant=ctx.merchant,
                kind=matched_rule.kind,
                payment_type=ctx.default_payment_type,
                suggested_category=matched_rule.category,
                suggestion_source=source,
                confidence=conf,
                description=ctx.description,
                location=ctx.location,
            )
        return await super().handle(ctx)


class BankCategoryHandler(BaseClassificationHandler):
    """Camada 2.5: Mapeamento heurístico de categoria informada pelo banco."""

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if ctx.bank_category and ctx.default_kind == "EXPENSE":
            norm_bcat = _normalize(ctx.bank_category)
            mapped = BANK_CATEGORY_MAP.get(norm_bcat)
            if mapped is not None:
                sug_cat, conf = mapped
                return ClassificationResult(
                    merchant=ctx.merchant,
                    kind=ctx.default_kind,
                    payment_type=ctx.default_payment_type,
                    suggested_category=sug_cat,
                    suggestion_source="RULE",
                    confidence=conf,
                    description=ctx.description,
                    location=ctx.location,
                )
        return await super().handle(ctx)
```

### 2.3. Montagem Fluente da Cadeia no `ClassificationService`

```python
class ClassificationService:
    def __init__(
        self,
        rule_repo: CategoryRuleRepositoryProtocol,
        chain_head: ClassificationHandlerProtocol | None = None,
    ) -> None:
        self.rule_repo = rule_repo
        self._chain_head = chain_head or self._build_default_chain()

    def _build_default_chain(self) -> ClassificationHandlerProtocol:
        head = OwnTransferHandler(holder_names=self.get_own_holder_names())
        (
            head.set_next(InvoicePaymentHandler())
            .set_next(RefundHandler())
            .set_next(CardFeeHandler())
            .set_next(SalaryIncomeHandler())
            .set_next(BonusIncomeHandler())
            .set_next(InboundPixHandler())
            .set_next(RuleMemoryHandler(self.rule_repo))
            .set_next(BankCategoryHandler())
        )
        return head
```

---

## 3. Benefícios Diretos

- **Ordem de Custo Otimizada**: Os 7 primeiros handlers rodam 100% em memória ($O(1)$) e fazem *short-circuit* antes de tocar no PostgreSQL (`RuleMemoryHandler`).
- **Máximo de 1 a 2 condicionais por Handler**: Cumpre rigorosamente o limite do `AGENTS.md`.
- **Extensibilidade Aberta/Fechada (OCP)**: Adicionar uma regra para Nubank ou Itaú no futuro exige apenas criar um novo Handler e encadeá-lo com `.set_next(...)`, sem alterar nenhum handler existente.

---

## 4. Checklist de Execução e Testes (Fase 2)

- [x] Criar `finance_api/services/extractors.py` com o pipeline funcional de extração de merchant/localização.
- [x] Criar `finance_api/services/classification_chain.py` com `ClassificationHandlerProtocol`, `BaseClassificationHandler` e os handlers concretos.
- [x] Refatorar `ClassificationService` em `finance_api/services/classification.py` para delegar a `self._extractor_pipeline` e `self._chain_head.handle(ctx)`.
- [x] Garantir que todos os testes existentes em `finance_api/tests/services/test_classification_service.py` passem sem regressão e adicionar testes unitários isolados por handler.
