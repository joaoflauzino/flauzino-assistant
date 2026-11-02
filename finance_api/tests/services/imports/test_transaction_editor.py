from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.schemas.imports import StagedTransactionUpdate
from finance_api.services.imports.transaction_editor import StagedTransactionEditor

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
        "category": "mercado",
        "description": "Mercado",
        "status": "PENDING",
        "fingerprint": "fp",
    }
    return StagedTransaction(**{**base, **overrides})


def _editor(tx: StagedTransaction | None) -> tuple[StagedTransactionEditor, MagicMock, MagicMock]:
    tx_repo = MagicMock()
    tx_repo.get_by_id = AsyncMock(return_value=tx)
    tx_repo.save = AsyncMock(side_effect=lambda row: row)
    rule_repo = MagicMock()
    rule_repo.upsert_rule = AsyncMock()
    category_repo = MagicMock()
    category_repo.get_by_key = AsyncMock(return_value=MagicMock(key="mercado"))
    income_category_repo = MagicMock()
    income_category_repo.get_by_key = AsyncMock(return_value=MagicMock(key="salario"))
    presenter = MagicMock()
    presenter.to_tx_response = AsyncMock(return_value="response")
    editor = StagedTransactionEditor(
        tx_repo=tx_repo,
        rule_repo=rule_repo,
        category_repo=category_repo,
        income_category_repo=income_category_repo,
        presenter=presenter,
    )
    return editor, tx_repo, rule_repo


@pytest.mark.asyncio
async def test_update_kind_to_transfer_clears_category() -> None:
    tx = _staged()
    editor, tx_repo, _ = _editor(tx)

    response = await editor.update(tx.id, StagedTransactionUpdate(kind="TRANSFER"))

    assert response == "response"
    assert tx.kind == "TRANSFER"
    assert tx.category is None
    tx_repo.save.assert_awaited_once_with(tx)


@pytest.mark.asyncio
async def test_update_rejects_unknown_kind() -> None:
    tx = _staged()
    editor, _, _ = _editor(tx)

    with pytest.raises(ValidationError):
        await editor.update(tx.id, StagedTransactionUpdate(kind="UNKNOWN"))


@pytest.mark.asyncio
async def test_update_normalizes_category_and_validates_it() -> None:
    tx = _staged()
    editor, _, _ = _editor(tx)

    await editor.update(tx.id, StagedTransactionUpdate(category="  Mercado "))

    assert tx.category == "mercado"
    editor._category_repo.get_by_key.assert_awaited_once_with("mercado")


@pytest.mark.asyncio
async def test_update_rejects_unknown_expense_category() -> None:
    tx = _staged()
    editor, _, _ = _editor(tx)
    editor._category_repo.get_by_key = AsyncMock(return_value=None)

    with pytest.raises(ValidationError):
        await editor.update(tx.id, StagedTransactionUpdate(category="inexistente"))


@pytest.mark.asyncio
async def test_update_approved_requires_category_for_expense() -> None:
    tx = _staged(category=None)
    editor, _, _ = _editor(tx)

    with pytest.raises(ValidationError):
        await editor.update(tx.id, StagedTransactionUpdate(status="APPROVED"))


@pytest.mark.asyncio
async def test_update_rejects_invalid_status() -> None:
    tx = _staged()
    editor, _, _ = _editor(tx)

    with pytest.raises(ValidationError):
        await editor.update(tx.id, StagedTransactionUpdate(status="COMMITTED"))


@pytest.mark.asyncio
async def test_update_learns_rule_when_remember_is_enabled() -> None:
    tx = _staged()
    editor, _, rule_repo = _editor(tx)

    await editor.update(tx.id, StagedTransactionUpdate(description="Compra"))

    rule_repo.upsert_rule.assert_awaited_once_with(
        pattern="SUPERMERCADO",
        direction="OUT",
        kind="EXPENSE",
        category="mercado",
        source="LEARNED",
    )


@pytest.mark.asyncio
async def test_update_skips_rule_learning_when_disabled() -> None:
    tx = _staged()
    editor, _, rule_repo = _editor(tx)

    await editor.update(
        tx.id,
        StagedTransactionUpdate(description="Compra", remember=False),
    )

    rule_repo.upsert_rule.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_rejects_missing_and_committed_transactions() -> None:
    editor, _, _ = _editor(None)

    with pytest.raises(EntityNotFoundError):
        await editor.update(uuid4(), StagedTransactionUpdate(description="x"))

    committed = _staged(status="COMMITTED")
    editor, _, _ = _editor(committed)

    with pytest.raises(ValidationError):
        await editor.update(committed.id, StagedTransactionUpdate(description="x"))


@pytest.mark.asyncio
async def test_link_sets_committed_ids_and_status() -> None:
    spent_id = uuid4()
    tx = _staged(possible_duplicate_of_spent_id=spent_id)
    editor, tx_repo, _ = _editor(tx)

    response = await editor.link(tx.id)

    assert response == "response"
    assert tx.committed_spent_id == spent_id
    assert tx.status == "LINKED"
    tx_repo.save.assert_awaited_once_with(tx)


@pytest.mark.asyncio
async def test_link_requires_a_duplicate_reference() -> None:
    tx = _staged()
    editor, _, _ = _editor(tx)

    with pytest.raises(ValidationError):
        await editor.link(tx.id)


@pytest.mark.asyncio
async def test_link_rejects_missing_transaction() -> None:
    editor, _, _ = _editor(None)

    with pytest.raises(EntityNotFoundError):
        await editor.link(uuid4())
