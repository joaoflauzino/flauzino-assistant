from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.importers.schemas import ResolvedImportTarget
from finance_api.models.import_batches import ImportBatch
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.services.import_presenter import ImportBatchPresenter

SP_TZ = ZoneInfo("America/Sao_Paulo")


def _batch(**overrides) -> ImportBatch:
    base = {
        "id": uuid4(),
        "parser": "c6_checking_csv",
        "filename": "extrato.csv",
        "file_sha256": "abc",
        "total_rows": 3,
        "new_rows": 2,
        "duplicate_rows": 1,
        "possible_duplicates": 0,
        "ai_used": False,
        "created_at": datetime(2026, 10, 3, 13, 0, tzinfo=SP_TZ),
    }
    return ImportBatch(**{**base, **overrides})


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
        "confidence": Decimal("0.800"),
    }
    return StagedTransaction(**{**base, **overrides})


def _presenter(spent=None, income=None) -> ImportBatchPresenter:
    batch_repo = MagicMock()
    batch_repo.get_counts_by_status = AsyncMock(return_value={"pending": 2})
    account_repo = MagicMock()
    account_repo.get_by_id = AsyncMock(return_value=None)
    credit_card_repo = MagicMock()
    credit_card_repo.get_by_id = AsyncMock(return_value=None)
    spent_service = MagicMock()
    spent_service.repo.get_by_id = AsyncMock(return_value=spent)
    income_service = MagicMock()
    income_service.repo.get_by_id = AsyncMock(return_value=income)
    return ImportBatchPresenter(
        batch_repo=batch_repo,
        account_repo=account_repo,
        credit_card_repo=credit_card_repo,
        spent_service=spent_service,
        income_service=income_service,
    )


def test_build_batch_response_includes_target_and_counts() -> None:
    presenter = _presenter()
    card_id = uuid4()
    target = ResolvedImportTarget(
        account_id=None,
        credit_card_id=card_id,
        target_key="c6_card",
        target_name="C6 Carbon Black",
    )

    response = presenter.build_batch_response(_batch(), target, {"pending": 2})

    assert response.account_name == "C6 Carbon Black"
    assert response.credit_card_id == card_id
    assert response.credit_card_name == "C6 Carbon Black"
    assert response.counts == {"pending": 2}


@pytest.mark.asyncio
async def test_build_batch_list_falls_back_to_card_name() -> None:
    presenter = _presenter()
    card_id = uuid4()
    card = MagicMock(id=card_id)
    card.name = "C6 Carbon Black"
    presenter._credit_card_repo.get_by_id = AsyncMock(return_value=card)
    batch = _batch(credit_card_id=card_id)

    responses = await presenter.build_batch_list([batch])

    assert len(responses) == 1
    assert responses[0].credit_card_name == "C6 Carbon Black"
    assert responses[0].account_name == "C6 Carbon Black"
    assert responses[0].counts == {"pending": 2}


@pytest.mark.asyncio
async def test_to_tx_response_maps_amount_and_missing_duplicate() -> None:
    presenter = _presenter()

    response = await presenter.to_tx_response(_staged())

    assert response.amount == Decimal("100.00")
    assert response.confidence == 0.8
    assert response.possible_duplicate is None


@pytest.mark.asyncio
async def test_to_tx_response_builds_spent_duplicate_info() -> None:
    spent_id = uuid4()
    spent = MagicMock(
        id=spent_id,
        item_bought="Mercado",
        amount=Decimal("100.00"),
        created_at=datetime(2026, 9, 30, 10, 0, tzinfo=SP_TZ),
    )
    presenter = _presenter(spent=spent)

    response = await presenter.to_tx_response(
        _staged(possible_duplicate_of_spent_id=spent_id),
    )

    assert response.possible_duplicate is not None
    assert response.possible_duplicate.type == "spent"
    assert response.possible_duplicate.label == "Mercado"


@pytest.mark.asyncio
async def test_to_tx_response_builds_income_duplicate_info() -> None:
    income_id = uuid4()
    income = MagicMock(
        id=income_id,
        description="Salário",
        amount=Decimal("5000.00"),
        received_at=datetime(2026, 9, 30, 10, 0, tzinfo=SP_TZ),
    )
    presenter = _presenter(income=income)

    response = await presenter.to_tx_response(
        _staged(possible_duplicate_of_income_id=income_id),
    )

    assert response.possible_duplicate is not None
    assert response.possible_duplicate.type == "income"
    assert response.possible_duplicate.label == "Salário"
