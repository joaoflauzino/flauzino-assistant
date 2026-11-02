"""Unit tests for the commit strategies and duplicate detectors of staged import rows."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.schemas.enums import CommitOutcomeStatus
from finance_api.schemas.imports import CommitContext
from finance_api.services.imports.commit_strategies import (
    ExpenseCommitStrategy,
    ExpenseDuplicateDetector,
    IncomeCommitStrategy,
    IncomeDuplicateDetector,
    NonRecordCommitStrategy,
    build_default_commit_strategies,
    build_default_duplicate_detectors,
)
from finance_api.services.incomes import IncomeService
from finance_api.services.spents import SpentService

SP_TZ = ZoneInfo("America/Sao_Paulo")


def _make_tx(
    *,
    kind: str = "EXPENSE",
    category: str | None = "mercado",
    status: str = "APPROVED",
    merchant: str = "SUPERMERCADO",
    direction: str = "OUT",
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
    )


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
    tx_exp_no_cat = _make_tx(kind="EXPENSE", category=None)
    res_fail = await exp_strategy.commit(tx_exp_no_cat, ctx)
    assert res_fail.status == CommitOutcomeStatus.FAILED
    assert res_fail.error_message == "Despesa sem categoria"

    # Expense with category -> committed_spent
    tx_exp = _make_tx(kind="EXPENSE", category="mercado")
    res_exp = await exp_strategy.commit(tx_exp, ctx)
    assert res_exp.status == CommitOutcomeStatus.COMMITTED_SPENT
    assert tx_exp.committed_spent_id == created_spent_id
    assert tx_exp.status == "COMMITTED"

    # Income without category -> failed
    tx_inc_no_cat = _make_tx(kind="INCOME", category=None)
    res_inc_fail = await inc_strategy.commit(tx_inc_no_cat, ctx)
    assert res_inc_fail.status == CommitOutcomeStatus.FAILED
    assert res_inc_fail.error_message == "Receita sem categoria"

    # Income with category -> committed_income
    tx_inc = _make_tx(kind="INCOME", category="salario", direction="IN")
    tx_inc.competence_date = date(2026, 9, 30)
    res_inc = await inc_strategy.commit(tx_inc, ctx)
    assert res_inc.status == CommitOutcomeStatus.COMMITTED_INCOME
    assert tx_inc.committed_income_id == created_income_id
    assert tx_inc.status == "COMMITTED"

    # Non-record (TRANSFER / INVOICE_PAYMENT / REFUND) -> processed_without_record
    tx_transfer = _make_tx(kind="TRANSFER", category=None)
    res_non_rec = await non_rec_strategy.commit(tx_transfer, ctx)
    assert res_non_rec.status == CommitOutcomeStatus.PROCESSED_WITHOUT_RECORD
    assert tx_transfer.status == "COMMITTED"


def test_commit_strategy_builder_registers_all_expected_keys() -> None:
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


@pytest.mark.asyncio
async def test_expense_duplicate_detector_maps_the_match_to_a_spent_id() -> None:
    spent_id = uuid4()
    tx_repo = MagicMock()
    tx_repo.find_possible_duplicate_spent = AsyncMock(return_value=MagicMock(id=spent_id))

    result = await ExpenseDuplicateDetector().detect(
        tx_repo=tx_repo,
        account_id=uuid4(),
        credit_card_id=None,
        amount=Decimal("120.50"),
        tx_date=date(2026, 10, 10),
    )

    assert result == (spent_id, None)
    tx_repo.find_possible_duplicate_spent.assert_awaited_once()


@pytest.mark.asyncio
async def test_income_duplicate_detector_maps_the_match_to_an_income_id() -> None:
    income_id = uuid4()
    tx_repo = MagicMock()
    tx_repo.find_possible_duplicate_income = AsyncMock(return_value=MagicMock(id=income_id))

    result = await IncomeDuplicateDetector().detect(
        tx_repo=tx_repo,
        account_id=uuid4(),
        credit_card_id=None,
        amount=Decimal("5000.00"),
        tx_date=date(2026, 10, 1),
    )

    assert result == (None, income_id)


@pytest.mark.asyncio
async def test_duplicate_detectors_return_empty_tuple_without_a_match() -> None:
    tx_repo = MagicMock()
    tx_repo.find_possible_duplicate_spent = AsyncMock(return_value=None)
    tx_repo.find_possible_duplicate_income = AsyncMock(return_value=None)

    expense = await ExpenseDuplicateDetector().detect(
        tx_repo=tx_repo,
        account_id=None,
        credit_card_id=uuid4(),
        amount=Decimal("10.00"),
        tx_date=date(2026, 10, 10),
    )
    income = await IncomeDuplicateDetector().detect(
        tx_repo=tx_repo,
        account_id=None,
        credit_card_id=None,
        amount=Decimal("10.00"),
        tx_date=date(2026, 10, 10),
    )

    assert expense == (None, None)
    assert income == (None, None)


def test_default_duplicate_detectors_cover_expense_and_income() -> None:
    detectors = build_default_duplicate_detectors()

    assert set(detectors.keys()) == {"EXPENSE", "INCOME"}
    assert isinstance(detectors["EXPENSE"], ExpenseDuplicateDetector)
    assert isinstance(detectors["INCOME"], IncomeDuplicateDetector)
