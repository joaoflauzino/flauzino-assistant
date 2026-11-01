"""Unit tests for BulkActionStrategy and TransactionCommitStrategy implementations."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.category_rules import CategoryRuleRepositoryProtocol
from finance_api.schemas.enums import (
    BulkActionType,
    CommitOutcomeStatus,
    StepOutcomeStatus,
)
from finance_api.schemas.imports import BulkActionRequest, CommitContext
from finance_api.services.import_strategies import (
    ApproveBulkStrategy,
    ExpenseCommitStrategy,
    IgnoreBulkStrategy,
    IncomeCommitStrategy,
    NonRecordCommitStrategy,
    ReopenBulkStrategy,
    SetCategoryBulkStrategy,
    build_default_bulk_strategies,
    build_default_commit_strategies,
)
from finance_api.services.incomes import IncomeService
from finance_api.services.protocols import (
    CategoryLookupProtocol,
    IncomeCategoryLookupProtocol,
)
from finance_api.services.spents import SpentService

SP_TZ = ZoneInfo("America/Sao_Paulo")


def _make_tx(
    *,
    kind: str = "EXPENSE",
    category: str | None = "mercado",
    status: str = "PENDING",
    merchant: str = "SUPERMERCADO",
    direction: str = "OUT",
    dup_spent: bool = False,
    dup_income: bool = False,
) -> StagedTransaction:
    return StagedTransaction(
        id=uuid4(),
        batch_id=uuid4(),
        account_id=uuid4(),
        occurred_at=datetime(2026, 10, 10, 12, 0, tzinfo=SP_TZ),
        raw_title=merchant,
        merchant=merchant,
        amount=Decimal("120.50"),
        direction=direction,
        kind=kind,
        payment_type="DEBIT",
        category=category,
        description="Compra teste",
        location="Uberlândia",
        status=status,
        fingerprint="fp-test",
        possible_duplicate_of_spent_id=uuid4() if dup_spent else None,
        possible_duplicate_of_income_id=uuid4() if dup_income else None,
    )


@pytest.mark.asyncio
async def test_approve_bulk_strategy_skips_possible_duplicates() -> None:
    rule_repo = MagicMock(spec=CategoryRuleRepositoryProtocol)
    rule_repo.upsert_rule = AsyncMock()
    strategy = ApproveBulkStrategy(rule_repo=rule_repo)

    tx_dup = _make_tx(dup_spent=True)
    req = BulkActionRequest(ids=[tx_dup.id], action=BulkActionType.APPROVE, remember=True)

    outcome = await strategy.execute(tx_dup, req)

    assert outcome.status == StepOutcomeStatus.SKIPPED
    assert tx_dup.status == "PENDING"
    rule_repo.upsert_rule.assert_not_called()


@pytest.mark.asyncio
async def test_approve_bulk_strategy_skips_missing_category_on_expense_or_income() -> None:
    rule_repo = MagicMock(spec=CategoryRuleRepositoryProtocol)
    rule_repo.upsert_rule = AsyncMock()
    strategy = ApproveBulkStrategy(rule_repo=rule_repo)

    tx_uncat = _make_tx(kind="EXPENSE", category=None)
    req = BulkActionRequest(ids=[tx_uncat.id], action=BulkActionType.APPROVE, remember=True)

    outcome = await strategy.execute(tx_uncat, req)

    assert outcome.status == StepOutcomeStatus.SKIPPED
    assert tx_uncat.status == "PENDING"
    rule_repo.upsert_rule.assert_not_called()


@pytest.mark.asyncio
async def test_approve_bulk_strategy_approves_and_learns_rule() -> None:
    rule_repo = MagicMock(spec=CategoryRuleRepositoryProtocol)
    rule_repo.upsert_rule = AsyncMock()
    strategy = ApproveBulkStrategy(rule_repo=rule_repo)

    tx = _make_tx(kind="EXPENSE", category="mercado", merchant="PADARIA CENTRAL")
    req = BulkActionRequest(ids=[tx.id], action=BulkActionType.APPROVE, remember=True)

    outcome = await strategy.execute(tx, req)

    assert outcome.status == StepOutcomeStatus.UPDATED
    assert tx.status == "APPROVED"
    rule_repo.upsert_rule.assert_awaited_once_with(
        pattern="PADARIA CENTRAL",
        direction="OUT",
        kind="EXPENSE",
        category="mercado",
        source="LEARNED",
    )


@pytest.mark.asyncio
async def test_ignore_and_reopen_bulk_strategies() -> None:
    ignore_strategy = IgnoreBulkStrategy()
    reopen_strategy = ReopenBulkStrategy()

    tx = _make_tx(status="PENDING")
    req_ignore = BulkActionRequest(ids=[tx.id], action=BulkActionType.IGNORE)
    out_ignore = await ignore_strategy.execute(tx, req_ignore)
    assert out_ignore.status == StepOutcomeStatus.UPDATED
    assert tx.status == "IGNORED"

    req_reopen = BulkActionRequest(ids=[tx.id], action=BulkActionType.REOPEN)
    out_reopen = await reopen_strategy.execute(tx, req_reopen)
    assert out_reopen.status == StepOutcomeStatus.UPDATED
    assert tx.status == "PENDING"


@pytest.mark.asyncio
async def test_set_category_bulk_strategy_validation_and_success() -> None:
    cat_repo = MagicMock(spec=CategoryLookupProtocol)
    inc_cat_repo = MagicMock(spec=IncomeCategoryLookupProtocol)
    rule_repo = MagicMock(spec=CategoryRuleRepositoryProtocol)
    rule_repo.upsert_rule = AsyncMock()

    strategy = SetCategoryBulkStrategy(
        category_repo=cat_repo,
        income_category_repo=inc_cat_repo,
        rule_repo=rule_repo,
    )

    tx_exp = _make_tx(kind="EXPENSE", category=None)

    # 1. Empty category -> skipped
    out_skip = await strategy.execute(
        tx_exp,
        BulkActionRequest(ids=[tx_exp.id], action=BulkActionType.SET_CATEGORY, category=None),
    )
    assert out_skip.status == StepOutcomeStatus.SKIPPED

    # 2. Non-existent expense category -> error
    cat_repo.get_by_key = AsyncMock(return_value=None)
    out_err = await strategy.execute(
        tx_exp,
        BulkActionRequest(
            ids=[tx_exp.id],
            action=BulkActionType.SET_CATEGORY,
            category="inexistente",
        ),
    )
    assert out_err.status == StepOutcomeStatus.ERROR
    assert out_err.error_message == "Categoria 'inexistente' não existe"

    # 3. Valid expense category -> updated + learned rule
    cat_repo.get_by_key = AsyncMock(return_value=MagicMock(key="moradia"))
    out_ok = await strategy.execute(
        tx_exp,
        BulkActionRequest(
            ids=[tx_exp.id],
            action=BulkActionType.SET_CATEGORY,
            category="  MORADIA ",
            remember=True,
        ),
    )
    assert out_ok.status == StepOutcomeStatus.UPDATED
    assert tx_exp.category == "moradia"
    rule_repo.upsert_rule.assert_awaited_once()

    # 4. Non-existent income category -> error
    tx_inc = _make_tx(kind="INCOME", direction="IN", category=None)
    inc_cat_repo.get_by_key = AsyncMock(return_value=None)
    out_inc_err = await strategy.execute(
        tx_inc,
        BulkActionRequest(
            ids=[tx_inc.id],
            action=BulkActionType.SET_CATEGORY,
            category="bonus_invalido",
        ),
    )
    assert out_inc_err.status == StepOutcomeStatus.ERROR
    assert out_inc_err.error_message == "Categoria 'bonus_invalido' não existe"


@pytest.mark.asyncio
async def test_commit_strategies_expense_income_and_non_record() -> None:
    spent_service = MagicMock(spec=SpentService)
    created_spent_id = uuid4()
    spent_service.create = AsyncMock(return_value=MagicMock(id=created_spent_id))

    income_service = MagicMock(spec=IncomeService)
    created_income_id = uuid4()
    income_service.create = AsyncMock(return_value=MagicMock(id=created_income_id))

    exp_strategy = ExpenseCommitStrategy(spent_service=spent_service)
    inc_strategy = IncomeCommitStrategy(income_service=income_service)
    non_rec_strategy = NonRecordCommitStrategy()

    ctx = CommitContext(
        payment_method_key="c6_joao",
        payment_type_value="DEBIT",
        account_id=uuid4(),
    )

    # Expense without category -> failed
    tx_exp_no_cat = _make_tx(kind="EXPENSE", category=None, status="APPROVED")
    res_fail = await exp_strategy.commit(tx_exp_no_cat, ctx)
    assert res_fail.status == CommitOutcomeStatus.FAILED
    assert res_fail.error_message == "Despesa sem categoria"

    # Expense with category -> committed_spent
    tx_exp = _make_tx(kind="EXPENSE", category="mercado", status="APPROVED")
    res_exp = await exp_strategy.commit(tx_exp, ctx)
    assert res_exp.status == CommitOutcomeStatus.COMMITTED_SPENT
    assert tx_exp.committed_spent_id == created_spent_id
    assert tx_exp.status == "COMMITTED"

    # Income without category -> failed
    tx_inc_no_cat = _make_tx(kind="INCOME", category=None, status="APPROVED")
    res_inc_fail = await inc_strategy.commit(tx_inc_no_cat, ctx)
    assert res_inc_fail.status == CommitOutcomeStatus.FAILED
    assert res_inc_fail.error_message == "Receita sem categoria"

    # Income with category -> committed_income
    tx_inc = _make_tx(kind="INCOME", category="salario", status="APPROVED")
    tx_inc.competence_date = date(2026, 9, 30)
    res_inc = await inc_strategy.commit(tx_inc, ctx)
    assert res_inc.status == CommitOutcomeStatus.COMMITTED_INCOME
    assert tx_inc.committed_income_id == created_income_id
    assert tx_inc.status == "COMMITTED"

    # Non-record (TRANSFER / INVOICE_PAYMENT / REFUND) -> processed_without_record
    tx_transfer = _make_tx(kind="TRANSFER", category=None, status="APPROVED")
    res_non_rec = await non_rec_strategy.commit(tx_transfer, ctx)
    assert res_non_rec.status == CommitOutcomeStatus.PROCESSED_WITHOUT_RECORD
    assert tx_transfer.status == "COMMITTED"


def test_strategy_builders_register_all_expected_keys() -> None:
    bulk_map = build_default_bulk_strategies(
        rule_repo=MagicMock(),
        category_repo=MagicMock(),
        income_category_repo=MagicMock(),
    )
    assert set(bulk_map.keys()) == {"approve", "ignore", "reopen", "set_category"}

    commit_map = build_default_commit_strategies(
        spent_service=MagicMock(),
        income_service=MagicMock(),
    )
    assert set(commit_map.keys()) == {
        "EXPENSE",
        "INCOME",
        "TRANSFER",
        "INVOICE_PAYMENT",
        "REFUND",
    }
