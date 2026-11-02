from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.schemas.enums import StepOutcomeStatus
from finance_api.schemas.imports import BulkActionRequest, StepOutcome
from finance_api.services.import_bulk import ImportBulkService

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
        "status": "PENDING",
        "fingerprint": "fp",
    }
    return StagedTransaction(**{**base, **overrides})


@pytest.mark.asyncio
async def test_execute_counts_updated_skipped_and_missing_rows() -> None:
    updatable = _staged()
    committed = _staged(status="COMMITTED")
    missing_id = uuid4()
    strategy = MagicMock()
    strategy.execute = AsyncMock(return_value=StepOutcome(status=StepOutcomeStatus.UPDATED))
    rows = {updatable.id: updatable, committed.id: committed}
    tx_repo = MagicMock()
    tx_repo.get_by_id = AsyncMock(side_effect=lambda tx_id: rows.get(tx_id))
    tx_repo.save = AsyncMock(side_effect=lambda tx: tx)
    service = ImportBulkService(tx_repo=tx_repo, bulk_strategies={"approve": strategy})

    result = await service.execute(
        BulkActionRequest(ids=[updatable.id, committed.id, missing_id], action="approve"),
    )

    assert result.updated == 1
    assert result.skipped == 1
    assert len(result.errors) == 1
    assert result.errors[0].id == missing_id
    tx_repo.save.assert_awaited_once_with(updatable)


@pytest.mark.asyncio
async def test_execute_reports_unknown_action_per_row() -> None:
    tx = _staged()
    tx_repo = MagicMock()
    tx_repo.get_by_id = AsyncMock(return_value=tx)
    tx_repo.save = AsyncMock()
    service = ImportBulkService(tx_repo=tx_repo, bulk_strategies={})

    result = await service.execute(BulkActionRequest(ids=[tx.id], action="invalid"))

    assert result.updated == 0
    assert result.skipped == 0
    assert "Ação desconhecida" in result.errors[0].error
    tx_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_surfaces_validation_errors_without_saving() -> None:
    tx = _staged()
    strategy = MagicMock()
    strategy.execute = AsyncMock(
        return_value=StepOutcome(
            status=StepOutcomeStatus.ERROR,
            error_message="Categoria inválida",
        ),
    )
    tx_repo = MagicMock()
    tx_repo.get_by_id = AsyncMock(return_value=tx)
    tx_repo.save = AsyncMock()
    service = ImportBulkService(tx_repo=tx_repo, bulk_strategies={"approve": strategy})

    result = await service.execute(BulkActionRequest(ids=[tx.id], action="approve"))

    assert result.errors[0].error == "Categoria inválida"
    tx_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_marks_skipped_strategy_outcome() -> None:
    tx = _staged()
    strategy = MagicMock()
    strategy.execute = AsyncMock(return_value=StepOutcome(status=StepOutcomeStatus.SKIPPED))
    tx_repo = MagicMock()
    tx_repo.get_by_id = AsyncMock(return_value=tx)
    tx_repo.save = AsyncMock()
    service = ImportBulkService(tx_repo=tx_repo, bulk_strategies={"approve": strategy})

    result = await service.execute(BulkActionRequest(ids=[tx.id], action="approve"))

    assert result.skipped == 1
    assert result.updated == 0
    tx_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_captures_strategy_exceptions_as_errors() -> None:
    tx = _staged()
    strategy = MagicMock()
    strategy.execute = AsyncMock(side_effect=RuntimeError("boom"))
    tx_repo = MagicMock()
    tx_repo.get_by_id = AsyncMock(return_value=tx)
    tx_repo.save = AsyncMock()
    service = ImportBulkService(tx_repo=tx_repo, bulk_strategies={"approve": strategy})

    result = await service.execute(BulkActionRequest(ids=[tx.id], action="approve"))

    assert result.errors[0].error == "boom"
    tx_repo.save.assert_not_awaited()
