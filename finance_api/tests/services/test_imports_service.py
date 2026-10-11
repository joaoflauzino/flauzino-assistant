from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo
import pytest

from finance_api.core.exceptions import EntityConflictError
from finance_api.models.accounts import Account
from finance_api.models.import_batches import ImportBatch
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.accounts import AccountRepository
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.category_rules import CategoryRuleRepository
from finance_api.repositories.credit_cards import CreditCardRepository
from finance_api.repositories.income_categories import IncomeCategoryRepository
from finance_api.repositories.imports import ImportBatchRepository
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.schemas.imports import (
    CommitRequest,
)
from finance_api.services.ai_classifier import AIClassifierClient
from finance_api.services.classification import ClassificationService
from finance_api.services.imports import ImportService
from finance_api.services.incomes import IncomeService
from finance_api.services.spents import SpentService

SAMPLE_CSV = b"""\xef\xbb\xbfEXTRATO DE CONTA CORRENTE C6 BANK\r
\r
Ag\xc3\xaancia: 1 / Conta: 145118436\r
Extrato gerado em 03/10/2026 - as 13:34:58\r
\r
Extrato de 04/08/2026 a 03/10/2026\r
\r
\r
Data Lan\xc3\xa7amento,Data Cont\xc3\xa1bil,T\xc3\xadtulo,Descri\xc3\xa7\xc3\xa3o,Entrada(R$),Sa\xc3\xadda(R$),Saldo do Dia(R$)\r
05/08/2026,05/08/2026,PGTO FAT CARTAO C6,Fatura de cart\xc3\xa3o,0.00,1000.00,1000.00\r
07/08/2026,07/08/2026,Pix enviado para CEMIG,TRANSF ENVIADA PIX,0.00,150.00,850.00\r
10/08/2026,10/08/2026,CRED SALARIO MENSAL,C6 BANK,5000.00,0.00,5850.00\r
"""


@pytest.fixture
def mock_dependencies():
    acc_id = uuid4()
    mock_acc = Account(id=acc_id, key="c6_joao", name="C6 (João Lucas)")

    batch_repo = MagicMock(spec=ImportBatchRepository)
    batch_repo.db = MagicMock()
    batch_repo.db.commit = AsyncMock()
    batch_repo.db.refresh = AsyncMock()
    batch_repo.get_by_sha256 = AsyncMock(return_value=None)

    def _mock_batch_create(b):
        b.id = uuid4()
        b.created_at = datetime.now(ZoneInfo("America/Sao_Paulo"))
        return b

    batch_repo.create = AsyncMock(side_effect=_mock_batch_create)
    batch_repo.get_counts_by_status = AsyncMock(return_value={"pending": 3, "approved": 0})
    batch_repo.list_all = AsyncMock(return_value=[])
    batch_repo.get_global_summary = AsyncMock(return_value={"pending": 3, "approved": 0})

    tx_repo = MagicMock(spec=StagedTransactionRepository)
    tx_repo.get_existing_fingerprints = AsyncMock(return_value=set())
    tx_repo.find_possible_duplicate_spent = AsyncMock(return_value=None)
    tx_repo.find_possible_duplicate_income = AsyncMock(return_value=None)
    tx_repo.create_many = AsyncMock(side_effect=lambda txs: txs)
    tx_repo.save = AsyncMock(side_effect=lambda tx: tx)

    rule_repo = MagicMock(spec=CategoryRuleRepository)
    rule_repo.find_matching_rule = AsyncMock(return_value=None)
    rule_repo.increment_hits = AsyncMock()
    rule_repo.upsert_rule = AsyncMock()

    acc_repo = MagicMock(spec=AccountRepository)
    acc_repo.get_by_id = AsyncMock(return_value=mock_acc)

    cc_repo = MagicMock(spec=CreditCardRepository)
    cc_repo.get_by_id = AsyncMock(return_value=None)

    spent_service = MagicMock(spec=SpentService)
    spent_service.create = AsyncMock(return_value=MagicMock(id=uuid4()))
    spent_service.repo = MagicMock()
    spent_service.repo.get_by_id = AsyncMock(return_value=None)

    income_service = MagicMock(spec=IncomeService)
    income_service.create = AsyncMock(return_value=MagicMock(id=uuid4()))
    income_service.repo = MagicMock()
    income_service.repo.get_by_id = AsyncMock(return_value=None)

    cat_repo = MagicMock(spec=CategoryRepository)
    cat_repo.get_by_key = AsyncMock(return_value=MagicMock(key="moradia"))
    cat_repo.list = AsyncMock(return_value=([], 0))

    inc_cat_repo = MagicMock(spec=IncomeCategoryRepository)
    inc_cat_repo.get_by_key = AsyncMock(return_value=MagicMock(key="salario"))
    inc_cat_repo.list = AsyncMock(return_value=([], 0))

    clf_service = ClassificationService(rule_repo=rule_repo)

    ai_client = MagicMock(spec=AIClassifierClient)
    ai_client.classify_batch = AsyncMock(return_value=({}, False))

    service = ImportService(
        batch_repo=batch_repo,
        tx_repo=tx_repo,
        rule_repo=rule_repo,
        classification_service=clf_service,
        account_repo=acc_repo,
        credit_card_repo=cc_repo,
        spent_service=spent_service,
        income_service=income_service,
        category_repo=cat_repo,
        income_category_repo=inc_cat_repo,
        ai_client=ai_client,
    )

    return service, acc_id, batch_repo, tx_repo, spent_service, income_service, rule_repo


@pytest.mark.asyncio
async def test_upload_batch_success(mock_dependencies):
    service, acc_id, batch_repo, tx_repo, _, _, _ = mock_dependencies

    res = await service.create_batch_from_upload(
        file_bytes=SAMPLE_CSV,
        filename="c6.csv",
        account_id=acc_id,
    )

    assert res.filename == "c6.csv"
    assert res.total_rows == 3
    assert res.new_rows == 3
    assert res.duplicate_rows == 0
    batch_repo.create.assert_called_once()
    tx_repo.create_many.assert_called_once()


@pytest.mark.asyncio
async def test_upload_duplicate_file_raises_conflict(mock_dependencies):
    service, acc_id, batch_repo, _, _, _, _ = mock_dependencies
    batch_repo.get_by_sha256 = AsyncMock(
        return_value=ImportBatch(
            id=uuid4(),
            created_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
        )
    )

    with pytest.raises(EntityConflictError):
        await service.create_batch_from_upload(
            file_bytes=SAMPLE_CSV,
            filename="c6.csv",
            account_id=acc_id,
        )


@pytest.mark.asyncio
async def test_commit_approved_processes_expense_income_and_transfers(mock_dependencies):
    service, acc_id, _, tx_repo, spent_service, income_service, _ = mock_dependencies

    tx_exp = StagedTransaction(
        id=uuid4(),
        batch_id=uuid4(),
        account_id=acc_id,
        occurred_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
        raw_title="CEMIG",
        merchant="CEMIG",
        amount=Decimal("150.00"),
        direction="OUT",
        kind="EXPENSE",
        payment_type="DEBIT",
        category="moradia",
        description="Conta Luz",
        location="Brasil",
        status="APPROVED",
        fingerprint="fp1",
    )
    tx_inc = StagedTransaction(
        id=uuid4(),
        batch_id=uuid4(),
        account_id=acc_id,
        occurred_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
        raw_title="Salário",
        merchant="C6 BANK",
        amount=Decimal("5000.00"),
        direction="IN",
        kind="INCOME",
        payment_type="OTHER",
        category="salario",
        description="Salário",
        location="Brasil",
        status="APPROVED",
        fingerprint="fp2",
    )
    tx_transf = StagedTransaction(
        id=uuid4(),
        batch_id=uuid4(),
        account_id=acc_id,
        occurred_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
        raw_title="PGTO FATURA",
        merchant="C6 BANK",
        amount=Decimal("1000.00"),
        direction="OUT",
        kind="INVOICE_PAYMENT",
        payment_type="DEBIT",
        category=None,
        description="Fatura C6",
        location="Brasil",
        status="APPROVED",
        fingerprint="fp3",
    )

    tx_repo.get_approved_for_commit = AsyncMock(return_value=[tx_exp, tx_inc, tx_transf])

    result = await service.commit_approved(CommitRequest())

    assert result.committed_spents == 1
    assert result.committed_incomes == 1
    assert result.processed_without_record == 1
    assert len(result.failed) == 0

    spent_service.create.assert_called_once()
    income_service.create.assert_called_once()
    assert tx_exp.status == "COMMITTED"
    assert tx_inc.status == "COMMITTED"
    assert tx_transf.status == "COMMITTED"


@pytest.mark.asyncio
async def test_link_transaction_to_existing_spent(mock_dependencies):
    service, _, _, tx_repo, _, _, _ = mock_dependencies
    existing_spent_id = uuid4()
    tx = StagedTransaction(
        id=uuid4(),
        batch_id=uuid4(),
        occurred_at=datetime.now(ZoneInfo("America/Sao_Paulo")),
        raw_title="Mercado",
        merchant="Mercado",
        amount=Decimal("50.00"),
        direction="OUT",
        kind="EXPENSE",
        payment_type="DEBIT",
        category="mercado",
        description="Mercado",
        location="Brasil",
        status="PENDING",
        fingerprint="fp_dup",
        possible_duplicate_of_spent_id=existing_spent_id,
    )
    tx_repo.get_by_id = AsyncMock(return_value=tx)

    res = await service.link_transaction(tx.id)

    assert res.status == "LINKED"
    assert tx.committed_spent_id == existing_spent_id
    assert tx.status == "LINKED"


@pytest.mark.asyncio
async def test_upload_credit_card_batch_and_commit(mock_dependencies):
    service, acc_id, batch_repo, tx_repo, spent_service, _, _ = mock_dependencies

    card_id = uuid4()
    mock_card = MagicMock(id=card_id, key="c6_card_joao", name="C6 Carbon Black", account_id=acc_id)
    service.credit_card_repo.get_by_id = AsyncMock(return_value=mock_card)
    service.credit_card_repo.list = AsyncMock(return_value=([mock_card], 1))

    card_csv = (
        "Data de Compra;Nome no Cartão;Final do Cartão;Categoria;Descrição;Parcela;Valor (em US$);Cotação (em R$);Valor (em R$)\n"
        "26/05/2026;JOAO L F CASSIANO;1141;Empresa para empresa;DELL;4/12;0;0;235.25\n"
        "05/09/2026;JOAO L F CASSIANO;1633;-;Inclusao de Pagamento;Única;0;0;-3610.14\n"
    ).encode("utf-8")

    res = await service.create_batch_from_upload(
        file_bytes=card_csv,
        filename="Fatura_2026-10-05.csv",
        credit_card_id=card_id,
    )

    assert res.total_rows == 2
    assert res.new_rows == 2
    tx_repo.create_many.assert_called()
    staged_items = tx_repo.create_many.call_args[0][0]
    assert len(staged_items) == 2

    # Check DELL installment and card digits
    st_dell = staged_items[0]
    assert st_dell.raw_title == "DELL"
    assert st_dell.current_installment == 4
    assert st_dell.total_installments == 12
    assert st_dell.card_last_digits == "1141"
    assert st_dell.credit_card_id == card_id

    # Check Inclusao de Pagamento
    st_pgto = staged_items[1]
    assert st_pgto.kind == "INVOICE_PAYMENT"
    assert st_pgto.amount == Decimal("3610.14")
    assert st_pgto.direction == "IN"

    # Test commit of credit card items
    st_dell.category = "compras"
    st_dell.status = "APPROVED"
    st_pgto.status = "APPROVED"

    tx_repo.get_approved_for_commit = AsyncMock(return_value=[st_dell, st_pgto])

    commit_res = await service.commit_approved(CommitRequest())
    assert commit_res.committed_spents == 1
    assert commit_res.processed_without_record == 1

    # Verify spent creation arguments
    spent_call_data = spent_service.create.call_args[0][0]
    assert spent_call_data.credit_card_id == card_id
    assert spent_call_data.payment_type == "CREDIT"
    assert spent_call_data.is_installment is False
    assert spent_call_data.current_installment == 4
    assert spent_call_data.total_installments == 12


@pytest.mark.asyncio
async def test_salary_competence_date_early_month(mock_dependencies):
    from datetime import date

    service, acc_id, _, tx_repo, _, _, _ = mock_dependencies

    salary_csv = (
        """Data Lançamento,Data Contábil,Título,Descrição,Entrada(R$),Saída(R$),Saldo do Dia(R$)
01/10/2026,01/10/2026,CRED SALARIO MENSAL,C6 BANK,5000.00,0.00,5000.00
20/09/2026,20/09/2026,ADTO SALARIO,C6 BANK,3000.00,0.00,8000.00
"""
    ).encode("utf-8")

    res = await service.create_batch_from_upload(
        file_bytes=salary_csv,
        filename="c6_salary.csv",
        account_id=acc_id,
    )
    assert res.total_rows == 2

    staged_items = tx_repo.create_many.call_args[0][0]
    assert len(staged_items) == 2

    st_oct = staged_items[0]
    assert st_oct.competence_date == date(2026, 9, 30)

    st_sep = staged_items[1]
    assert st_sep.competence_date == date(2026, 9, 20)
