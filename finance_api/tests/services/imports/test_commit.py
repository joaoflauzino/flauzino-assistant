from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.schemas.enums import CommitOutcomeStatus
from finance_api.schemas.imports import CommitRequest, CommitStepOutcome
from finance_api.services.imports.commit import CommitContextResolver, ImportCommitService

SP_TZ = ZoneInfo("America/Sao_Paulo")


def _staged(**overrides) -> StagedTransaction:
    base = {
        "id": uuid4(),
        "batch_id": uuid4(),
        "occurred_at": datetime(2026, 10, 1, 9, 0, tzinfo=SP_TZ),
        "raw_title": "SUPERMERCADO",
        "merchant": "SUPERMERCADO",
        "amount": Decimal("100.00"),
        "direction": "OUT",
        "kind": "EXPENSE",
        "payment_type": "DEBIT",
        "description": "Mercado",
        "status": "APPROVED",
        "fingerprint": "fp",
    }
    return StagedTransaction(**{**base, **overrides})


@pytest.mark.asyncio
async def test_resolver_prefers_credit_card_context() -> None:
    card = MagicMock(key="c6_card", account_id=uuid4())
    credit_card_repo = MagicMock()
    credit_card_repo.get_by_id = AsyncMock(return_value=card)
    resolver = CommitContextResolver(account_repo=MagicMock(), credit_card_repo=credit_card_repo)
    tx = _staged(credit_card_id=uuid4(), account_id=None)

    context = await resolver.resolve(tx)

    assert context.payment_method_key == "c6_card"
    assert context.payment_type_value == "CREDIT"
    assert context.account_id == card.account_id


@pytest.mark.asyncio
async def test_resolver_falls_back_to_account_and_defaults_payment_type() -> None:
    account = MagicMock(key="c6_joao")
    account_repo = MagicMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    resolver = CommitContextResolver(
        account_repo=account_repo,
        credit_card_repo=MagicMock(),
    )
    tx = _staged(account_id=uuid4(), payment_type="UNKNOWN")

    context = await resolver.resolve(tx)

    assert context.payment_method_key == "c6_joao"
    assert context.payment_type_value == "DEBIT"


@pytest.mark.asyncio
async def test_commit_counts_outcomes_and_saves_transactions() -> None:
    spent_tx = _staged()
    income_tx = _staged(kind="INCOME", direction="IN")
    transfer_tx = _staged(kind="TRANSFER")
    tx_repo = MagicMock()
    tx_repo.get_approved_for_commit = AsyncMock(
        return_value=[spent_tx, income_tx, transfer_tx],
    )
    tx_repo.save = AsyncMock(side_effect=lambda tx: tx)
    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=MagicMock())
    spent_strategy = MagicMock()
    spent_strategy.commit = AsyncMock(
        return_value=CommitStepOutcome(status=CommitOutcomeStatus.COMMITTED_SPENT),
    )
    income_strategy = MagicMock()
    income_strategy.commit = AsyncMock(
        return_value=CommitStepOutcome(status=CommitOutcomeStatus.COMMITTED_INCOME),
    )
    transfer_strategy = MagicMock()
    transfer_strategy.commit = AsyncMock(
        return_value=CommitStepOutcome(status=CommitOutcomeStatus.PROCESSED_WITHOUT_RECORD),
    )
    service = ImportCommitService(
        tx_repo=tx_repo,
        context_resolver=resolver,
        commit_strategies={
            "EXPENSE": spent_strategy,
            "INCOME": income_strategy,
            "TRANSFER": transfer_strategy,
        },
    )

    result = await service.commit(CommitRequest())

    assert result.committed_spents == 1
    assert result.committed_incomes == 1
    assert result.processed_without_record == 1
    assert result.failed == []
    assert tx_repo.save.await_count == 3


@pytest.mark.asyncio
async def test_commit_records_strategy_failures_without_saving() -> None:
    tx = _staged()
    tx_repo = MagicMock()
    tx_repo.get_approved_for_commit = AsyncMock(return_value=[tx])
    tx_repo.save = AsyncMock()
    strategy = MagicMock()
    strategy.commit = AsyncMock(
        return_value=CommitStepOutcome(
            status=CommitOutcomeStatus.FAILED,
            error_message="falhou",
        ),
    )
    service = ImportCommitService(
        tx_repo=tx_repo,
        context_resolver=MagicMock(resolve=AsyncMock(return_value=MagicMock())),
        commit_strategies={"EXPENSE": strategy},
    )

    result = await service.commit(CommitRequest())

    assert len(result.failed) == 1
    assert result.failed[0].error == "falhou"
    tx_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_commit_records_unexpected_exception_per_transaction() -> None:
    tx = _staged()
    tx_repo = MagicMock()
    tx_repo.get_approved_for_commit = AsyncMock(return_value=[tx])
    tx_repo.save = AsyncMock()
    strategy = MagicMock()
    strategy.commit = AsyncMock(side_effect=RuntimeError("boom"))
    service = ImportCommitService(
        tx_repo=tx_repo,
        context_resolver=MagicMock(resolve=AsyncMock(return_value=MagicMock())),
        commit_strategies={"EXPENSE": strategy},
    )

    result = await service.commit(CommitRequest())

    assert result.failed[0].error == "boom"
    tx_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_commit_ignores_kinds_without_strategy() -> None:
    tx = _staged(kind="REFUND")
    tx_repo = MagicMock()
    tx_repo.get_approved_for_commit = AsyncMock(return_value=[tx])
    tx_repo.save = AsyncMock()
    service = ImportCommitService(
        tx_repo=tx_repo,
        context_resolver=MagicMock(),
        commit_strategies={},
    )

    result = await service.commit(CommitRequest())

    assert result.committed_spents == 0
    tx_repo.save.assert_not_awaited()
