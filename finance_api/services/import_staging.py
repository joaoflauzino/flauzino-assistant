"""Staging builder: classifies, deduplicates, and materialises imported rows."""

from uuid import UUID

from finance_api.importers.schemas import ParsedTransaction, ResolvedImportTarget
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.services.classification import ClassificationResult, ClassificationService
from finance_api.services.import_strategies import (
    DuplicateDetectorStrategy,
    resolve_salary_competence_date,
)


class StagingBuilder:
    """Transforms parsed bank rows into pending :class:`StagedTransaction` entities."""

    def __init__(
        self,
        tx_repo: StagedTransactionRepository,
        classification_service: ClassificationService,
        duplicate_detectors: dict[str, DuplicateDetectorStrategy],
    ) -> None:
        self._tx_repo = tx_repo
        self._classification_service = classification_service
        self._duplicate_detectors = duplicate_detectors

    async def build(
        self,
        batch_id: UUID,
        target: ResolvedImportTarget,
        new_pairs: list[tuple[ParsedTransaction, str]],
        is_credit_card: bool,
    ) -> tuple[list[StagedTransaction], int]:
        """Classifies every new row and returns the staged entities plus duplicate count."""
        staged_list: list[StagedTransaction] = []
        possible_duplicates_count = 0

        for tx, fingerprint in new_pairs:
            classification = await self._classify(tx, is_credit_card)
            duplicate_spent_id, duplicate_income_id = await self._detect_duplicates(
                classification.kind,
                target,
                tx,
            )
            if duplicate_spent_id or duplicate_income_id:
                possible_duplicates_count += 1

            staged_list.append(
                self._to_staged(
                    batch_id=batch_id,
                    target=target,
                    tx=tx,
                    classification=classification,
                    fingerprint=fingerprint,
                    duplicate_spent_id=duplicate_spent_id,
                    duplicate_income_id=duplicate_income_id,
                )
            )

        return staged_list, possible_duplicates_count

    async def _classify(
        self,
        tx: ParsedTransaction,
        is_credit_card: bool,
    ) -> ClassificationResult:
        return await self._classification_service.classify_transaction(
            tx.raw_title,
            tx.raw_description,
            tx.direction,
            tx.amount,
            bank_category=tx.bank_category,
            is_credit_card=is_credit_card,
        )

    async def _detect_duplicates(
        self,
        kind: str,
        target: ResolvedImportTarget,
        tx: ParsedTransaction,
    ) -> tuple[UUID | None, UUID | None]:
        detector = self._duplicate_detectors.get(kind)
        if detector is None:
            return None, None
        return await detector.detect(
            tx_repo=self._tx_repo,
            account_id=target.account_id,
            credit_card_id=target.credit_card_id,
            amount=tx.amount,
            tx_date=tx.occurred_at.date(),
        )

    def _to_staged(
        self,
        batch_id: UUID,
        target: ResolvedImportTarget,
        tx: ParsedTransaction,
        classification: ClassificationResult,
        fingerprint: str,
        duplicate_spent_id: UUID | None,
        duplicate_income_id: UUID | None,
    ) -> StagedTransaction:
        competence_date = resolve_salary_competence_date(
            kind=classification.kind,
            occurred_at=tx.occurred_at,
            raw_title=tx.raw_title,
            raw_description=tx.raw_description,
        )
        return StagedTransaction(
            batch_id=batch_id,
            account_id=target.account_id,
            credit_card_id=target.credit_card_id,
            occurred_at=tx.occurred_at,
            posted_at=tx.posted_at,
            raw_title=tx.raw_title,
            raw_description=tx.raw_description,
            raw_row=tx.raw_row,
            merchant=classification.merchant,
            amount=tx.amount,
            direction=tx.direction,
            kind=classification.kind,
            payment_type=classification.payment_type,
            suggested_category=classification.suggested_category,
            suggestion_source=classification.suggestion_source,
            confidence=classification.confidence,
            category=classification.suggested_category,
            description=classification.description[:50],
            location=classification.location,
            status="PENDING",
            fingerprint=fingerprint,
            current_installment=tx.current_installment,
            total_installments=tx.total_installments,
            card_last_digits=tx.card_last_digits,
            competence_date=competence_date,
            possible_duplicate_of_spent_id=duplicate_spent_id,
            possible_duplicate_of_income_id=duplicate_income_id,
        )
