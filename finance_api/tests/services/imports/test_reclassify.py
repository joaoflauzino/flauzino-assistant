from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.services.imports.reclassify import ImportReclassifyService

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
async def test_reclassify_without_candidates_short_circuits() -> None:
    tx_repo = MagicMock()
    tx_repo.list_for_reclassification = AsyncMock(return_value=[])
    service = ImportReclassifyService(
        tx_repo=tx_repo,
        rule_repo=MagicMock(),
        enrichment_service=MagicMock(),
    )

    result = await service.reclassify()

    assert result.total_reclassified == 0
    assert result.applied_rules == 0
    assert result.applied_ai == 0


@pytest.mark.asyncio
async def test_reclassify_applies_matching_rules_and_increments_hits() -> None:
    tx = _staged()
    rule = MagicMock(id=uuid4(), category="mercado", source="SEED", hits=2)
    tx_repo = MagicMock()
    tx_repo.list_for_reclassification = AsyncMock(return_value=[tx])
    tx_repo.save = AsyncMock(side_effect=lambda row: row)
    rule_repo = MagicMock()
    rule_repo.find_matching_rule = AsyncMock(return_value=rule)
    rule_repo.increment_hits = AsyncMock()
    enrichment_service = MagicMock()
    enrichment_service.enrich_candidates = AsyncMock(return_value=[])
    service = ImportReclassifyService(
        tx_repo=tx_repo,
        rule_repo=rule_repo,
        enrichment_service=enrichment_service,
    )

    result = await service.reclassify()

    assert result.applied_rules == 1
    assert result.applied_ai == 0
    assert tx.category == "mercado"
    assert tx.suggestion_source == "RULE"
    assert tx.confidence == Decimal("0.950")
    rule_repo.increment_hits.assert_awaited_once_with(rule.id)
    enrichment_service.enrich_candidates.assert_not_awaited()


@pytest.mark.asyncio
async def test_reclassify_delegates_unmatched_rows_to_ai() -> None:
    tx = _staged()
    tx_repo = MagicMock()
    tx_repo.list_for_reclassification = AsyncMock(return_value=[tx])
    tx_repo.save = AsyncMock(side_effect=lambda row: row)
    rule_repo = MagicMock()
    rule_repo.find_matching_rule = AsyncMock(return_value=None)
    enrichment_service = MagicMock()
    enrichment_service.enrich_candidates = AsyncMock(return_value=[tx])
    service = ImportReclassifyService(
        tx_repo=tx_repo,
        rule_repo=rule_repo,
        enrichment_service=enrichment_service,
    )

    result = await service.reclassify(batch_id=uuid4())

    assert result.applied_rules == 0
    assert result.applied_ai == 1
    assert result.total_reclassified == 1
    enrichment_service.enrich_candidates.assert_awaited_once_with([tx])
    tx_repo.save.assert_awaited_once_with(tx)


@pytest.mark.asyncio
async def test_reclassify_treats_rule_without_category_as_ai_candidate() -> None:
    tx = _staged()
    rule = MagicMock(id=uuid4(), category=None, source="SEED", hits=1)
    tx_repo = MagicMock()
    tx_repo.list_for_reclassification = AsyncMock(return_value=[tx])
    tx_repo.save = AsyncMock()
    rule_repo = MagicMock()
    rule_repo.find_matching_rule = AsyncMock(return_value=rule)
    rule_repo.increment_hits = AsyncMock()
    enrichment_service = MagicMock()
    enrichment_service.enrich_candidates = AsyncMock(return_value=[])
    service = ImportReclassifyService(
        tx_repo=tx_repo,
        rule_repo=rule_repo,
        enrichment_service=enrichment_service,
    )

    result = await service.reclassify()

    assert result.applied_rules == 0
    rule_repo.increment_hits.assert_not_awaited()
    enrichment_service.enrich_candidates.assert_awaited_once_with([tx])
