"""Concrete handlers and builder for the transaction classification Chain of Responsibility."""

from collections.abc import Sequence
from decimal import Decimal

from finance_api.repositories.category_rules import CategoryRuleRepositoryProtocol
from finance_api.schemas.classification import (
    BANK_CATEGORY_MAP,
    ClassificationContext,
    ClassificationResult,
    PaymentType,
    SuggestionSource,
    TransactionKind,
)
from finance_api.services.protocols import (
    BaseClassificationHandler,
    ClassificationHandlerProtocol,
)
from finance_api.utils.text import _normalize


class OwnTransferHandler(BaseClassificationHandler):
    def __init__(self, holder_names: Sequence[str]) -> None:
        super().__init__()
        self._holder_names = holder_names

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if any(name and name in ctx.norm_combined for name in self._holder_names):
            return ClassificationResult(
                merchant=ctx.merchant,
                kind=TransactionKind.TRANSFER,
                payment_type=(
                    PaymentType.PIX if "PIX" in ctx.norm_combined else PaymentType.TRANSFER
                ),
                suggested_category=None,
                suggestion_source=SuggestionSource.RULE,
                confidence=Decimal("1.000"),
                description=ctx.description,
                location=ctx.location,
            )
        return await super().handle(ctx)


class InvoicePaymentHandler(BaseClassificationHandler):
    PATTERNS: tuple[str, ...] = (
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
                kind=TransactionKind.INVOICE_PAYMENT,
                payment_type=PaymentType.CREDIT if ctx.is_credit_card else PaymentType.DEBIT,
                suggested_category=None,
                suggestion_source=SuggestionSource.RULE,
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
                kind=TransactionKind.REFUND,
                payment_type=PaymentType.CREDIT if ctx.is_credit_card else PaymentType.PIX,
                suggested_category=None,
                suggestion_source=SuggestionSource.RULE,
                confidence=Decimal("0.950"),
                description=ctx.description,
                location=ctx.location,
            )
        return await super().handle(ctx)


class CardFeeHandler(BaseClassificationHandler):
    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if "ANUIDADE" in ctx.norm_title:
            return ClassificationResult(
                merchant="C6 BANK",
                kind=TransactionKind.EXPENSE,
                payment_type=PaymentType.CREDIT,
                suggested_category="servicos",
                suggestion_source=SuggestionSource.RULE,
                confidence=Decimal("0.950"),
                description=ctx.description,
                location=ctx.location,
            )
        return await super().handle(ctx)


class SalaryIncomeHandler(BaseClassificationHandler):
    KEYWORDS: tuple[str, ...] = ("CRED SALARIO", "ADTO SALARIO")

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if any(k in ctx.norm_title for k in self.KEYWORDS):
            return ClassificationResult(
                merchant="C6 BANK",
                kind=TransactionKind.INCOME,
                payment_type=PaymentType.OTHER,
                suggested_category="salario",
                suggestion_source=SuggestionSource.RULE,
                confidence=Decimal("0.980"),
                description=ctx.description,
                location=ctx.location,
            )
        return await super().handle(ctx)


class BonusIncomeHandler(BaseClassificationHandler):
    KEYWORDS: tuple[str, ...] = ("PPR", "PLR")

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if any(k in ctx.norm_title for k in self.KEYWORDS):
            return ClassificationResult(
                merchant="C6 BANK",
                kind=TransactionKind.INCOME,
                payment_type=PaymentType.OTHER,
                suggested_category="premiacao",
                suggestion_source=SuggestionSource.RULE,
                confidence=Decimal("0.980"),
                description=ctx.description,
                location=ctx.location,
            )
        return await super().handle(ctx)


class InboundPixHandler(BaseClassificationHandler):
    KEYWORDS: tuple[str, ...] = ("PIX RECEBIDO", "TRANSF RECEBIDA")

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if ctx.direction == "IN" and any(k in ctx.norm_title for k in self.KEYWORDS):
            return ClassificationResult(
                merchant=ctx.merchant,
                kind=TransactionKind.INCOME,
                payment_type=PaymentType.PIX,
                suggested_category="pix",
                suggestion_source=SuggestionSource.RULE,
                confidence=Decimal("0.800"),
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
            source = (
                SuggestionSource.RULE if matched_rule.source == "SEED" else SuggestionSource.MEMORY
            )
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
        if ctx.bank_category and ctx.default_kind == TransactionKind.EXPENSE:
            norm_bcat = _normalize(ctx.bank_category)
            mapped = BANK_CATEGORY_MAP.get(norm_bcat)
            if mapped is not None:
                sug_cat, conf = mapped
                return ClassificationResult(
                    merchant=ctx.merchant,
                    kind=ctx.default_kind,
                    payment_type=ctx.default_payment_type,
                    suggested_category=sug_cat,
                    suggestion_source=SuggestionSource.RULE,
                    confidence=conf,
                    description=ctx.description,
                    location=ctx.location,
                )
        return await super().handle(ctx)


def build_default_classification_chain(
    holder_names: Sequence[str],
    rule_repo: CategoryRuleRepositoryProtocol,
) -> ClassificationHandlerProtocol:
    """Builds and links the default Chain of Responsibility for transaction classification."""
    head = OwnTransferHandler(holder_names=holder_names)
    (
        head.set_next(InvoicePaymentHandler())
        .set_next(RefundHandler())
        .set_next(CardFeeHandler())
        .set_next(SalaryIncomeHandler())
        .set_next(BonusIncomeHandler())
        .set_next(InboundPixHandler())
        .set_next(RuleMemoryHandler(rule_repo))
        .set_next(BankCategoryHandler())
    )
    return head
