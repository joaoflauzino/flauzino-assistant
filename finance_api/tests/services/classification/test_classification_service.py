from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from finance_api.core.exceptions import EntityNotFoundError
from finance_api.models.category_rules import CategoryRule
from finance_api.repositories.category_rules import CategoryRuleRepository
from finance_api.schemas.classification import (
    ClassificationContext,
    ClassificationResult,
    ExtractedMerchantInfo,
    RawTransactionText,
)
from finance_api.services.classification.chain import BaseClassificationHandler
from finance_api.services.classification.service import ClassificationService


@pytest.fixture
def mock_rule_repo():
    repo = MagicMock(spec=CategoryRuleRepository)
    repo.increment_hits = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_list_and_delete_rules_service(mock_rule_repo):
    rule = CategoryRule(id=uuid4(), pattern="CEMIG", direction="OUT", kind="EXPENSE")
    mock_rule_repo.list_all = AsyncMock(return_value=[rule])
    mock_rule_repo.delete_by_id = AsyncMock(side_effect=[True, False])

    service = ClassificationService(rule_repo=mock_rule_repo)

    rules = await service.list_rules()
    assert list(rules) == [rule]

    await service.delete_rule(rule.id)

    with pytest.raises(EntityNotFoundError):
        await service.delete_rule(uuid4())


def test_is_own_transfer_helper(mock_rule_repo):
    service = ClassificationService(rule_repo=mock_rule_repo)
    assert service.is_own_transfer("Pix enviado para João Lucas Flauzino Cassiano") is True
    assert service.is_own_transfer("Compra na Padaria Central") is False


@pytest.mark.asyncio
async def test_classify_transfer_own_accounts(mock_rule_repo):
    service = ClassificationService(rule_repo=mock_rule_repo)

    # Transferência para João Lucas
    res = await service.classify_transaction(
        raw_title="Pix enviado para João Lucas Flauzino Cassiano",
        raw_description="TRANSF ENVIADA PIX",
        direction="OUT",
        amount=Decimal("100.00"),
    )
    assert res.kind == "TRANSFER"
    assert res.suggested_category is None
    assert res.confidence == Decimal("1.000")
    assert res.suggestion_source == "RULE"

    # Transferência para Lailla
    res2 = await service.classify_transaction(
        raw_title="Pix enviado para Lailla Nurrielle Campos Carvalho Flauzino",
        raw_description="TRANSF ENVIADA PIX",
        direction="OUT",
        amount=Decimal("300.00"),
    )
    assert res2.kind == "TRANSFER"

    # Transferência recebida de João Lucas
    res3 = await service.classify_transaction(
        raw_title="Pix recebido de João Lucas Flauzino Cassiano",
        raw_description="Pix recebido",
        direction="IN",
        amount=Decimal("233.30"),
    )
    assert res3.kind == "TRANSFER"


@pytest.mark.asyncio
async def test_classify_invoice_payments(mock_rule_repo):
    service = ClassificationService(rule_repo=mock_rule_repo)

    res = await service.classify_transaction(
        raw_title="PGTO FAT CARTAO C6",
        raw_description="Fatura de cartão",
        direction="OUT",
        amount=Decimal("3610.14"),
    )
    assert res.kind == "INVOICE_PAYMENT"
    assert res.payment_type == "DEBIT"
    assert res.suggested_category is None

    res2 = await service.classify_transaction(
        raw_title="NU PAGAMENTOS SA",
        raw_description="NU PAGAMENTOS SA",
        direction="OUT",
        amount=Decimal("1947.13"),
    )
    assert res2.kind == "INVOICE_PAYMENT"

    res3 = await service.classify_transaction(
        raw_title="BANCO BRADESCARD S A",
        raw_description="BANCO BRADESCARD S A",
        direction="OUT",
        amount=Decimal("445.88"),
    )
    assert res3.kind == "INVOICE_PAYMENT"


@pytest.mark.asyncio
async def test_classify_salaries_and_plr(mock_rule_repo):
    service = ClassificationService(rule_repo=mock_rule_repo)

    res = await service.classify_transaction(
        raw_title="CRED SALARIO MENSAL",
        raw_description="C6 BANK",
        direction="IN",
        amount=Decimal("6406.65"),
    )
    assert res.kind == "INCOME"
    assert res.suggested_category == "salario"

    res2 = await service.classify_transaction(
        raw_title="PAGAMENTO PPR/PLR",
        raw_description="C6 BANK",
        direction="IN",
        amount=Decimal("12288.53"),
    )
    assert res2.kind == "INCOME"
    assert res2.suggested_category == "premiacao"


@pytest.mark.asyncio
async def test_classify_merchant_rules(mock_rule_repo):
    mock_rule_repo.find_matching_rule = AsyncMock(
        return_value=CategoryRule(
            id=None,
            pattern="CEMIG",
            match_type="CONTAINS",
            direction="OUT",
            kind="EXPENSE",
            category="moradia",
            hits=5,
            source="SEED",
        )
    )
    service = ClassificationService(rule_repo=mock_rule_repo)

    res = await service.classify_transaction(
        raw_title="Pix enviado para CEMIG DISTRIBUICAO S.A",
        raw_description="TRANSF ENVIADA PIX",
        direction="OUT",
        amount=Decimal("462.73"),
    )
    assert res.kind == "EXPENSE"
    assert res.suggested_category == "moradia"
    assert res.suggestion_source == "RULE"
    mock_rule_repo.increment_hits.assert_called_once()


@pytest.mark.asyncio
async def test_classify_refund_and_anuidade(mock_rule_repo):
    mock_rule_repo.find_matching_rule = AsyncMock(return_value=None)
    service = ClassificationService(rule_repo=mock_rule_repo)

    # Devolução pix
    res_refund = await service.classify_transaction(
        raw_title="Devol recebida pix de Loja ABC",
        raw_description="Devolução",
        direction="IN",
        amount=Decimal("50.00"),
    )
    assert res_refund.kind == "REFUND"
    assert res_refund.confidence == Decimal("0.950")

    # Anuidade
    res_fee = await service.classify_transaction(
        raw_title="ANUIDADE CARTAO 12/12",
        raw_description="",
        direction="OUT",
        amount=Decimal("45.00"),
    )
    assert res_fee.kind == "EXPENSE"
    assert res_fee.suggested_category == "servicos"
    assert res_fee.payment_type == "CREDIT"


@pytest.mark.asyncio
async def test_classify_bank_category_and_inbound_pix(mock_rule_repo):
    mock_rule_repo.find_matching_rule = AsyncMock(return_value=None)
    service = ClassificationService(rule_repo=mock_rule_repo)

    # Inbound Pix de terceiros
    res_pix = await service.classify_transaction(
        raw_title="Pix recebido de Carlos Silva",
        raw_description="PIX RECEBIDO",
        direction="IN",
        amount=Decimal("150.00"),
    )
    assert res_pix.kind == "INCOME"
    assert res_pix.suggested_category == "pix"
    assert res_pix.payment_type == "PIX"

    # Bank Category map with is_credit_card=True
    res_bank = await service.classify_transaction(
        raw_title="BURGER KING",
        raw_description="",
        direction="OUT",
        amount=Decimal("35.00"),
        bank_category="RESTAURANTE / LANCHONETE / BAR",
        is_credit_card=True,
    )
    assert res_bank.kind == "EXPENSE"
    assert res_bank.payment_type == "CREDIT"
    assert res_bank.suggested_category == "comer_fora"
    assert res_bank.suggestion_source == "RULE"


@pytest.mark.asyncio
async def test_classification_service_custom_chain_and_extractor(mock_rule_repo):
    class CustomHeadHandler(BaseClassificationHandler):
        async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
            if "VIP" in ctx.norm_title:
                return ClassificationResult(
                    merchant="VIP MERCHANT",
                    kind="EXPENSE",
                    payment_type="OTHER",
                    suggested_category="vip_category",
                    suggestion_source="CUSTOM",
                    confidence=Decimal("1.000"),
                    description="VIP transaction",
                )
            return await super().handle(ctx)

    def custom_pipeline(raw: RawTransactionText) -> ExtractedMerchantInfo:
        return ExtractedMerchantInfo("CUSTOM_M", None, "custom_desc")

    custom_head = CustomHeadHandler()
    service = ClassificationService(
        rule_repo=mock_rule_repo,
        chain_head=custom_head,
        extractor_pipeline=custom_pipeline,
    )

    res_vip = await service.classify_transaction(
        raw_title="VIP ACCESS PURCHASE",
        raw_description="",
        direction="OUT",
        amount=Decimal("999.00"),
    )
    assert res_vip.suggested_category == "vip_category"
    assert res_vip.suggestion_source == "CUSTOM"

    res_normal = await service.classify_transaction(
        raw_title="NORMAL PURCHASE",
        raw_description="",
        direction="OUT",
        amount=Decimal("10.00"),
    )
    assert res_normal.merchant == "CUSTOM_M"
    assert res_normal.suggested_category is None
