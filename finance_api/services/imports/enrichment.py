"""LLM-powered batch enrichment shared by upload and reclassification flows."""

from collections.abc import Callable, Sequence
from decimal import Decimal
from typing import Any

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.protocols import (
    CategoryRepositoryProtocol,
    IncomeCategoryRepositoryProtocol,
)
from finance_api.services.classification.ai_classifier import AIClassifierClient

DEFAULT_CONFIDENCE = Decimal("0.750")
CANDIDATE_KINDS = ("EXPENSE", "INCOME")


class BatchEnrichmentService:
    """Requests category suggestions from the LLM for unclassified transactions."""

    def __init__(
        self,
        category_repo: CategoryRepositoryProtocol,
        income_category_repo: IncomeCategoryRepositoryProtocol,
        ai_client: AIClassifierClient,
    ) -> None:
        self._category_repo = category_repo
        self._income_category_repo = income_category_repo
        self._ai_client = ai_client

    async def enrich_staged(self, staged_list: list[StagedTransaction]) -> bool:
        """Enriches staged rows in place and reports whether the LLM responded."""
        candidates = [
            staged
            for staged in staged_list
            if staged.kind in CANDIDATE_KINDS and not staged.suggested_category
        ]
        if not candidates:
            return False

        suggestions, ai_success = await self._request(
            candidates,
            id_for=lambda index, _: str(index),
        )
        if not ai_success:
            return False

        for index, staged in enumerate(candidates):
            self._apply(staged, suggestions.get(str(index)))
        return True

    async def enrich_candidates(
        self,
        candidates: Sequence[StagedTransaction],
    ) -> list[StagedTransaction]:
        """Returns the candidates that received a valid LLM suggestion, mutated in place."""
        suggestions, ai_success = await self._request(
            candidates,
            id_for=lambda _, tx: str(tx.id),
        )
        if not ai_success:
            return []

        enriched: list[StagedTransaction] = []
        for tx in candidates:
            suggestion = suggestions.get(str(tx.id))
            if suggestion and suggestion[0]:
                self._apply(tx, suggestion)
                enriched.append(tx)
        return enriched

    async def _request(
        self,
        items: Sequence[StagedTransaction],
        id_for: Callable[[int, StagedTransaction], str],
    ) -> tuple[dict[str, tuple[str | None, float | None]], bool]:
        expense_categories, income_categories = await self._load_categories()
        payload = [
            self._build_payload_item(id_for(index, tx), tx) for index, tx in enumerate(items)
        ]
        return await self._ai_client.classify_batch(
            transactions=payload,
            expense_categories=expense_categories,
            income_categories=income_categories,
        )

    async def _load_categories(self) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        expense_cats, _ = await self._category_repo.list(skip=0, limit=200)
        income_cats, _ = await self._income_category_repo.list(skip=0, limit=200)
        return (
            [{"key": c.key, "display_name": c.display_name} for c in expense_cats],
            [{"key": c.key, "display_name": c.display_name} for c in income_cats],
        )

    def _build_payload_item(self, tx_id: str, tx: StagedTransaction) -> dict[str, Any]:
        return {
            "id": tx_id,
            "merchant": tx.merchant,
            "raw_title": tx.raw_title,
            "raw_description": tx.raw_description,
            "direction": tx.direction,
            "amount": float(tx.amount),
        }

    def _apply(
        self,
        tx: StagedTransaction,
        suggestion: tuple[str | None, float | None] | None,
    ) -> None:
        if suggestion is None:
            return
        category, confidence = suggestion
        if not category:
            return
        tx.suggested_category = category
        tx.category = category
        tx.suggestion_source = "LLM"
        tx.confidence = Decimal(str(confidence)) if confidence else DEFAULT_CONFIDENCE
