from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.models.category_rules import CategoryRule
from finance_api.repositories.category_rules import CategoryRuleRepository
from finance_api.schemas.classification import (
    ClassificationContext,
    ClassificationResult,
)
from finance_api.services.classification_chain import (
    BankCategoryHandler,
    BonusIncomeHandler,
    CardFeeHandler,
    InboundPixHandler,
    InvoicePaymentHandler,
    OwnTransferHandler,
    RefundHandler,
    RuleMemoryHandler,
    SalaryIncomeHandler,
    build_default_classification_chain,
)
from finance_api.services.protocols import BaseClassificationHandler
from finance_api.utils.text import normalize_upper


def _make_context(
    raw_title: str = "Padaria Central",
    raw_description: str | None = None,
    direction: str = "OUT",
    amount: Decimal = Decimal("50.00"),
    merchant: str = "Padaria Central",
    location: str | None = None,
    description: str = "Padaria Central",
    default_kind: str = "EXPENSE",
    default_payment_type: str = "DEBIT",
    bank_category: str | None = None,
    is_credit_card: bool = False,
) -> ClassificationContext:
    norm_title = normalize_upper(raw_title)
    norm_desc = normalize_upper(raw_description or "")
    norm_combined = f"{norm_title} {norm_desc}".strip()
    return ClassificationContext(
        raw_title=raw_title,
        raw_description=raw_description,
        norm_title=norm_title,
        norm_desc=norm_desc,
        norm_combined=norm_combined,
        direction=direction,
        amount=amount,
        merchant=merchant,
        location=location,
        description=description,
        default_kind=default_kind,
        default_payment_type=default_payment_type,
        bank_category=bank_category,
        is_credit_card=is_credit_card,
    )


class StubFallbackHandler(BaseClassificationHandler):
    """Stub handler to verify BaseClassificationHandler delegation."""

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        return await super().handle(ctx)


@pytest.mark.asyncio
async def test_base_handler_fallback_when_no_match() -> None:
    handler = StubFallbackHandler()
    ctx = _make_context(
        merchant="Lojinha",
        default_kind="EXPENSE",
        default_payment_type="CREDIT",
    )
    result = await handler.handle(ctx)
    assert result.merchant == "Lojinha"
    assert result.kind == "EXPENSE"
    assert result.payment_type == "CREDIT"
    assert result.suggested_category is None
    assert result.suggestion_source is None
    assert result.confidence is None


@pytest.mark.asyncio
async def test_own_transfer_handler_matches_and_delegates() -> None:
    handler = OwnTransferHandler(holder_names=["JOAO FLAVZ"])
    next_handler = AsyncMock()
    next_handler.handle = AsyncMock(
        return_value=ClassificationResult("Next", "EXPENSE", "DEBIT", None, None, None, "D")
    )
    handler.set_next(next_handler)

    # Matches
    ctx_match = _make_context(raw_title="Pix enviado para Joao Flavz", raw_description="PIX")
    res_match = await handler.handle(ctx_match)
    assert res_match.kind == "TRANSFER"
    assert res_match.payment_type == "PIX"
    assert res_match.confidence == Decimal("1.000")
    assert res_match.suggestion_source == "RULE"
    next_handler.handle.assert_not_called()

    # Delegates
    ctx_no_match = _make_context(raw_title="Padaria")
    await handler.handle(ctx_no_match)
    next_handler.handle.assert_called_once_with(ctx_no_match)


@pytest.mark.asyncio
async def test_invoice_payment_handler() -> None:
    handler = InvoicePaymentHandler()
    next_mock = AsyncMock()
    handler.set_next(next_mock)

    for pat in (
        "INCLUSAO DE PAGAMENTO",
        "PGTO FAT CARTAO",
        "FATURA DE CARTAO",
        "NU PAGAMENTOS",
        "BRADESCARD",
    ):
        ctx = _make_context(raw_title=f"LANCAMENTO {pat}", is_credit_card=False)
        res = await handler.handle(ctx)
        assert res.kind == "INVOICE_PAYMENT"
        assert res.merchant == "C6 BANK"
        assert res.payment_type == "DEBIT"

    ctx_cc = _make_context(raw_title="FATURA DE CARTAO", is_credit_card=True)
    res_cc = await handler.handle(ctx_cc)
    assert res_cc.payment_type == "CREDIT"

    ctx_none = _make_context(raw_title="Outra transação")
    await handler.handle(ctx_none)
    next_mock.handle.assert_called_once()


@pytest.mark.asyncio
async def test_refund_handler() -> None:
    handler = RefundHandler()
    next_mock = AsyncMock()
    handler.set_next(next_mock)

    ctx1 = _make_context(raw_title="DEVOL RECEBIDA PIX", is_credit_card=False)
    res1 = await handler.handle(ctx1)
    assert res1.kind == "REFUND"
    assert res1.payment_type == "PIX"
    assert res1.confidence == Decimal("0.950")

    ctx2 = _make_context(raw_title="ESTORNO COMPRA", is_credit_card=True)
    res2 = await handler.handle(ctx2)
    assert res2.kind == "REFUND"
    assert res2.payment_type == "CREDIT"

    ctx_none = _make_context(raw_title="Compra comum")
    await handler.handle(ctx_none)
    next_mock.handle.assert_called_once()


@pytest.mark.asyncio
async def test_card_fee_handler() -> None:
    handler = CardFeeHandler()
    next_mock = AsyncMock()
    handler.set_next(next_mock)

    ctx = _make_context(raw_title="ANUIDADE CARTAO TITULAR")
    res = await handler.handle(ctx)
    assert res.kind == "EXPENSE"
    assert res.suggested_category == "servicos"
    assert res.merchant == "C6 BANK"
    assert res.confidence == Decimal("0.950")

    ctx_none = _make_context(raw_title="Tarifa avulsa")
    await handler.handle(ctx_none)
    next_mock.handle.assert_called_once()


@pytest.mark.asyncio
async def test_salary_and_bonus_handlers() -> None:
    salary_handler = SalaryIncomeHandler()
    bonus_handler = BonusIncomeHandler()

    ctx_sal = _make_context(raw_title="CRED SALARIO MENSAL", direction="IN")
    res_sal = await salary_handler.handle(ctx_sal)
    assert res_sal.kind == "INCOME"
    assert res_sal.suggested_category == "salario"
    assert res_sal.confidence == Decimal("0.980")

    ctx_bonus = _make_context(raw_title="PLR 2026", direction="IN")
    res_bonus = await bonus_handler.handle(ctx_bonus)
    assert res_bonus.kind == "INCOME"
    assert res_bonus.suggested_category == "premiacao"
    assert res_bonus.confidence == Decimal("0.980")


@pytest.mark.asyncio
async def test_inbound_pix_handler() -> None:
    handler = InboundPixHandler()
    next_mock = AsyncMock()
    handler.set_next(next_mock)

    ctx_in = _make_context(
        raw_title="PIX RECEBIDO DE AMIGO",
        direction="IN",
        default_kind="INCOME",
    )
    res_in = await handler.handle(ctx_in)
    assert res_in.kind == "INCOME"
    assert res_in.payment_type == "PIX"
    assert res_in.suggested_category == "pix"
    assert res_in.confidence == Decimal("0.800")

    # If direction is OUT, should delegate
    ctx_out = _make_context(
        raw_title="PIX RECEBIDO DE AMIGO",
        direction="OUT",
    )
    await handler.handle(ctx_out)
    next_mock.handle.assert_called_once()


@pytest.mark.asyncio
async def test_rule_memory_handler() -> None:
    repo = MagicMock(spec=CategoryRuleRepository)
    rule_id = uuid4()
    rule = CategoryRule(
        id=rule_id,
        pattern="UBER",
        direction="OUT",
        kind="EXPENSE",
        category="transporte",
        hits=3,
        source="SEED",
    )
    repo.find_matching_rule = AsyncMock(return_value=rule)
    repo.increment_hits = AsyncMock()

    handler = RuleMemoryHandler(rule_repo=repo)
    ctx = _make_context(merchant="UBER TRIP", direction="OUT")
    res = await handler.handle(ctx)

    assert res.kind == "EXPENSE"
    assert res.suggested_category == "transporte"
    assert res.suggestion_source == "RULE"
    assert res.confidence == Decimal("0.950")
    repo.increment_hits.assert_called_once_with(rule_id)


@pytest.mark.asyncio
async def test_bank_category_handler() -> None:
    handler = BankCategoryHandler()
    next_mock = AsyncMock()
    handler.set_next(next_mock)

    ctx = _make_context(
        bank_category="RESTAURANTE / LANCHONETE / BAR",
        default_kind="EXPENSE",
    )
    res = await handler.handle(ctx)
    assert res.suggested_category == "comer_fora"
    assert res.confidence == Decimal("0.950")
    assert res.suggestion_source == "RULE"

    # Non-mapped bank category delegates
    ctx_unmapped = _make_context(
        bank_category="CATEGORIA DESCONHECIDA",
        default_kind="EXPENSE",
    )
    await handler.handle(ctx_unmapped)
    next_mock.handle.assert_called_once()


@pytest.mark.asyncio
async def test_build_default_classification_chain() -> None:
    repo = MagicMock(spec=CategoryRuleRepository)
    repo.find_matching_rule = AsyncMock(return_value=None)
    chain = build_default_classification_chain(
        holder_names=["JOAO FLAVZ"],
        rule_repo=repo,
    )
    ctx = _make_context(raw_title="Compra aleatoria", default_kind="EXPENSE")
    res = await chain.handle(ctx)
    assert res.suggested_category is None
    assert res.suggestion_source is None
