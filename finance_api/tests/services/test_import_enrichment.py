from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.services.import_enrichment import BatchEnrichmentService

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


def _service(classify_batch: AsyncMock) -> BatchEnrichmentService:
    category_repo = MagicMock()
    category_repo.list = AsyncMock(return_value=([], 0))
    income_category_repo = MagicMock()
    income_category_repo.list = AsyncMock(return_value=([], 0))
    ai_client = MagicMock()
    ai_client.classify_batch = classify_batch
    return BatchEnrichmentService(
        category_repo=category_repo,
        income_category_repo=income_category_repo,
        ai_client=ai_client,
    )


@pytest.mark.asyncio
async def test_enrich_staged_skips_when_there_are_no_candidates() -> None:
    classify_batch = AsyncMock()
    service = _service(classify_batch)

    enriched = await service.enrich_staged([_staged(suggested_category="mercado")])

    assert enriched is False
    classify_batch.assert_not_awaited()


@pytest.mark.asyncio
async def test_enrich_staged_applies_tuple_suggestions() -> None:
    first = _staged()
    second = _staged()
    classify_batch = AsyncMock(
        return_value=({"0": ("mercado", 0.91), "1": (None, None)}, True),
    )
    service = _service(classify_batch)

    enriched = await service.enrich_staged([first, second])

    assert enriched is True
    assert first.category == "mercado"
    assert first.suggested_category == "mercado"
    assert first.suggestion_source == "LLM"
    assert first.confidence == Decimal("0.91")
    assert second.category is None


@pytest.mark.asyncio
async def test_enrich_staged_returns_false_when_llm_fails() -> None:
    classify_batch = AsyncMock(return_value=({}, False))
    service = _service(classify_batch)
    staged = _staged()

    assert await service.enrich_staged([staged]) is False
    assert staged.category is None


@pytest.mark.asyncio
async def test_enrich_candidates_only_returns_suggested_rows() -> None:
    suggested = _staged()
    skipped = _staged()
    classify_batch = AsyncMock(
        return_value=(
            {str(suggested.id): ("mercado", None), str(skipped.id): (None, 0.5)},
            True,
        ),
    )
    service = _service(classify_batch)

    enriched = await service.enrich_candidates([suggested, skipped])

    assert enriched == [suggested]
    assert suggested.confidence == Decimal("0.750")
    assert skipped.category is None
    payload = classify_batch.call_args.kwargs["transactions"]
    assert {item["id"] for item in payload} == {str(suggested.id), str(skipped.id)}
