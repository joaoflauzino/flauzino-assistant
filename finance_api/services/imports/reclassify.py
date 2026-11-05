"""Reclassification of pending staged transactions using rules and LLM suggestions."""

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.protocols import (
    CategoryRuleRepositoryProtocol,
    StagedTransactionRepositoryProtocol,
)
from finance_api.schemas.imports import ReclassifyResult
from finance_api.services.imports.enrichment import BatchEnrichmentService

RULE_CONFIDENCE_EXACT = Decimal("0.950")
RULE_CONFIDENCE_FUZZY = Decimal("0.850")


class ImportReclassifyService:
    """Re-runs the classification workflow for pending staged transactions."""

    def __init__(
        self,
        tx_repo: StagedTransactionRepositoryProtocol,
        rule_repo: CategoryRuleRepositoryProtocol,
        enrichment_service: BatchEnrichmentService,
    ) -> None:
        self._tx_repo = tx_repo
        self._rule_repo = rule_repo
        self._enrichment_service = enrichment_service

    async def reclassify(self, batch_id: UUID | None = None) -> ReclassifyResult:
        candidates = await self._tx_repo.list_for_reclassification(batch_id)
        if not candidates:
            return ReclassifyResult(total_reclassified=0, applied_rules=0, applied_ai=0)

        applied_rules, ai_candidates = await self._apply_rules(candidates)
        applied_ai = await self._apply_ai(ai_candidates)
        return ReclassifyResult(
            total_reclassified=applied_rules + applied_ai,
            applied_rules=applied_rules,
            applied_ai=applied_ai,
        )

    async def _apply_rules(
        self,
        candidates: Sequence[StagedTransaction],
    ) -> tuple[int, list[StagedTransaction]]:
        applied_rules = 0
        ai_candidates: list[StagedTransaction] = []

        for tx in candidates:
            rule = await self._rule_repo.find_matching_rule(tx.merchant, tx.direction)
            if not rule or not rule.category:
                ai_candidates.append(tx)
                continue

            tx.category = rule.category
            tx.suggested_category = rule.category
            tx.suggestion_source = "RULE" if rule.source == "SEED" else "MEMORY"
            tx.confidence = RULE_CONFIDENCE_EXACT if rule.hits >= 2 else RULE_CONFIDENCE_FUZZY
            await self._rule_repo.increment_hits(rule.id)
            await self._tx_repo.save(tx)
            applied_rules += 1

        return applied_rules, ai_candidates

    async def _apply_ai(self, candidates: Sequence[StagedTransaction]) -> int:
        if not candidates:
            return 0

        enriched = await self._enrichment_service.enrich_candidates(candidates)
        for tx in enriched:
            await self._tx_repo.save(tx)
        return len(enriched)
