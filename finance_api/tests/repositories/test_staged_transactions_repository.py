"""Unit tests for the staged-transaction filter/pagination query builder."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.staged_transactions import StagedTransactionRepository

pytestmark = pytest.mark.asyncio


def make_transaction(**overrides) -> StagedTransaction:
    fields = {
        "id": uuid4(),
        "batch_id": uuid4(),
        "occurred_at": datetime(2026, 9, 10, tzinfo=ZoneInfo("America/Sao_Paulo")),
        "raw_title": "Mercado",
        "amount": 100.0,
        "direction": "OUT",
        "kind": "EXPENSE",
        "status": "PENDING",
        "fingerprint": "fp_1",
    }
    fields.update(overrides)
    return StagedTransaction(**fields)


def build_session(total: int, items: list) -> AsyncMock:
    session = AsyncMock()
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = items
    session.execute.side_effect = [count_result, items_result]
    return session


def executed_statements(session: AsyncMock) -> tuple[str, str]:
    """Returns the compiled SQL of the count and items statements, in that order."""
    count_statement = session.execute.await_args_list[0].args[0]
    items_statement = session.execute.await_args_list[1].args[0]
    return str(count_statement.compile()), str(items_statement.compile())


async def test_list_by_filter_without_filters_keeps_queries_unfiltered():
    tx = make_transaction()
    session = build_session(total=1, items=[tx])

    items, total = await StagedTransactionRepository(session).list_by_filter()

    count_sql, items_sql = executed_statements(session)
    assert (items, total) == ([tx], 1)
    assert "WHERE" not in count_sql
    assert "WHERE" not in items_sql


async def test_list_by_filter_builds_every_condition():
    session = build_session(total=0, items=[])

    await StagedTransactionRepository(session).list_by_filter(
        batch_id=uuid4(),
        status="PENDING",
        kind="EXPENSE",
        only_duplicates=True,
        only_unclassified=True,
    )

    count_sql, items_sql = executed_statements(session)
    for sql in (count_sql, items_sql):
        assert "staged_transactions.batch_id" in sql
        assert "staged_transactions.status" in sql
        assert "staged_transactions.kind" in sql
        assert "possible_duplicate_of_spent_id" in sql
        assert "possible_duplicate_of_income_id" in sql
        assert "staged_transactions.category IS NULL" in sql


async def test_list_by_filter_applies_pagination_window():
    session = build_session(total=0, items=[])

    await StagedTransactionRepository(session).list_by_filter(page=3, size=25)

    _, items_sql = executed_statements(session)
    items_statement = session.execute.await_args_list[1].args[0]
    assert "LIMIT" in items_sql
    assert "OFFSET" in items_sql
    assert 25 in items_statement.compile().params.values()
    assert 50 in items_statement.compile().params.values()


async def test_list_by_filter_orders_by_occurrence_then_creation_desc():
    session = build_session(total=0, items=[])

    await StagedTransactionRepository(session).list_by_filter()

    _, items_sql = executed_statements(session)
    assert "ORDER BY staged_transactions.occurred_at DESC" in items_sql
    assert "staged_transactions.created_at DESC" in items_sql


async def test_list_by_filter_only_duplicates_matches_either_source():
    session = build_session(total=0, items=[])

    await StagedTransactionRepository(session).list_by_filter(only_duplicates=True)

    _, items_sql = executed_statements(session)
    assert "possible_duplicate_of_spent_id IS NOT NULL" in items_sql
    assert "possible_duplicate_of_income_id IS NOT NULL" in items_sql
    assert " OR " in items_sql


async def test_list_by_filter_only_unclassified_restricts_kinds():
    session = build_session(total=0, items=[])

    await StagedTransactionRepository(session).list_by_filter(only_unclassified=True)

    _, items_sql = executed_statements(session)
    assert "staged_transactions.kind IN" in items_sql
    assert "staged_transactions.category IS NULL" in items_sql


async def test_get_approved_for_commit_reuses_condition_builder():
    tx = make_transaction(status="APPROVED")
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [tx]
    session.execute.return_value = result
    batch_id = uuid4()

    items = await StagedTransactionRepository(session).get_approved_for_commit(batch_id=batch_id)

    statement = session.execute.await_args_list[0].args[0]
    sql = str(statement.compile())
    assert items == [tx]
    assert "staged_transactions.status" in sql
    assert "staged_transactions.batch_id" in sql
    assert "ORDER BY staged_transactions.occurred_at ASC" in sql
    assert batch_id in statement.compile().params.values()
