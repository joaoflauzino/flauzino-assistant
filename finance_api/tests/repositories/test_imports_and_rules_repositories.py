from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.text import normalize_upper
from finance_api.models.accounts import Account
from finance_api.models.category_rules import CategoryRule
from finance_api.models.import_batches import ImportBatch
from finance_api.repositories.base import SQLAlchemyRepository
from finance_api.repositories.category_rules import CategoryRuleRepository
from finance_api.repositories.imports import ImportBatchRepository

pytestmark = pytest.mark.asyncio


class DummyAccountRepo(SQLAlchemyRepository[Account, UUID]):
    model = Account


async def test_sqlalchemy_base_repository_methods() -> None:
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.add = MagicMock()

    entity_id = uuid4()
    acc = Account(id=entity_id, key="c6_test", name="C6 Test")
    mock_db.get.return_value = acc

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [acc]
    exec_res = MagicMock()
    exec_res.scalars.return_value = scalars_mock
    mock_db.execute.return_value = exec_res

    repo = DummyAccountRepo(mock_db)

    fetched = await repo.get_by_id(entity_id)
    assert fetched == acc
    mock_db.get.assert_awaited_once_with(Account, entity_id)

    listed = await repo.list_all(limit=10, offset=0)
    assert listed == [acc]
    mock_db.execute.assert_awaited_once()

    added = await repo.add(acc)
    assert added == acc
    mock_db.add.assert_called_once_with(acc)
    mock_db.commit.assert_awaited_once()
    mock_db.refresh.assert_awaited_once_with(acc)

    await repo.delete_entity(acc)
    mock_db.delete.assert_awaited_once_with(acc)


async def test_category_rule_repository_operations() -> None:
    assert normalize_upper("  São Paulo - Ação  ") == "SAO PAULO - ACAO"

    mock_db = AsyncMock(spec=AsyncSession)
    repo = CategoryRuleRepository(mock_db)

    now = datetime.now(ZoneInfo("America/Sao_Paulo"))
    rule_exact = CategoryRule(
        id=uuid4(),
        pattern="NETFLIX",
        match_type="EXACT",
        direction="OUT",
        kind="EXPENSE",
        category="servicos",
        hits=3,
        source="SEED",
        created_at=now,
        updated_at=now,
    )
    rule_contains = CategoryRule(
        id=uuid4(),
        pattern="CEMIG",
        match_type="CONTAINS",
        direction="OUT",
        kind="EXPENSE",
        category="moradia",
        hits=5,
        source="LEARNED",
        created_at=now,
        updated_at=now,
    )

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [rule_exact, rule_contains]
    list_res = MagicMock()
    list_res.scalars.return_value = scalars_mock
    mock_db.execute.return_value = list_res

    all_rules = await repo.list_all()
    assert len(all_rules) == 2

    # Match EXACT
    m1 = await repo.find_matching_rule("netflix", "OUT")
    assert m1 == rule_exact

    # Non-matching direction skipped, then CONTAINS matched
    m2 = await repo.find_matching_rule("Pix enviado CEMIG DISTRIBUICAO", "OUT")
    assert m2 == rule_contains

    # No match
    m3 = await repo.find_matching_rule("CEMIG", "IN")
    assert m3 is None
    m4 = await repo.find_matching_rule("PADARIA DO JOAO", "OUT")
    assert m4 is None

    # Increment hits
    await repo.increment_hits(rule_contains.id)
    mock_db.commit.assert_awaited()

    # Upsert rule
    upsert_res = MagicMock()
    upsert_res.scalar_one.return_value = rule_contains
    mock_db.execute.return_value = upsert_res
    upserted = await repo.upsert_rule(
        pattern="  CEMIG  ",
        direction="OUT",
        kind="EXPENSE",
        category="moradia",
    )
    assert upserted == rule_contains

    # Delete by id (found and not found)
    del_res_true = MagicMock()
    del_res_true.rowcount = 1
    mock_db.execute.return_value = del_res_true
    assert await repo.delete_by_id(rule_contains.id) is True

    del_res_false = MagicMock()
    del_res_false.rowcount = 0
    mock_db.execute.return_value = del_res_false
    assert await repo.delete_by_id(uuid4()) is False


async def test_import_batch_repository_operations() -> None:
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.add = MagicMock()
    repo = ImportBatchRepository(mock_db)

    batch_id = uuid4()
    batch = ImportBatch(
        id=batch_id,
        filename="extrato.csv",
        file_sha256="abc123sha",
        parser="c6_checking",
        total_rows=10,
        new_rows=8,
        duplicate_rows=2,
    )

    created = await repo.create(batch)
    assert created == batch
    mock_db.add.assert_called_with(batch)

    updated = await repo.update_batch_stats(batch, possible_duplicates=3, ai_used=True)
    assert updated.possible_duplicates == 3
    assert updated.ai_used is True

    single_res = MagicMock()
    single_res.scalar_one_or_none.return_value = batch
    mock_db.execute.return_value = single_res

    assert await repo.get_by_id(batch_id) == batch
    assert await repo.get_by_sha256("abc123sha") == batch

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [batch]
    list_res = MagicMock()
    list_res.scalars.return_value = scalars_mock
    mock_db.execute.return_value = list_res

    batches = await repo.list_all(limit=20)
    assert list(batches) == [batch]

    counts_res = MagicMock()
    counts_res.fetchall.return_value = [("PENDING", 4), ("APPROVED", 2), ("COMMITTED", 2)]
    mock_db.execute.return_value = counts_res
    counts = await repo.get_counts_by_status(batch_id)
    assert counts["pending"] == 4
    assert counts["approved"] == 2
    assert counts["committed"] == 2
    assert counts["ignored"] == 0

    summary_res = MagicMock()
    summary_res.fetchall.return_value = [("PENDING", 7), ("APPROVED", 1)]
    mock_db.execute.return_value = summary_res
    summary = await repo.get_global_summary()
    assert summary == {"pending": 7, "approved": 1}
