from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import pytest

from finance_api.models.category_rules import CategoryRule
from finance_api.repositories.category_rules import CategoryRuleRepository
from finance_api.services.classification import ClassificationService


@pytest.fixture
def mock_rule_repo():
    repo = MagicMock(spec=CategoryRuleRepository)
    repo.increment_hits = AsyncMock()
    return repo


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
