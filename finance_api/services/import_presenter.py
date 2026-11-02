"""Presentation helpers that map import entities to API response schemas."""

from decimal import Decimal
from uuid import UUID

from finance_api.importers.schemas import ResolvedImportTarget
from finance_api.models.import_batches import ImportBatch
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.accounts import AccountRepositoryProtocol
from finance_api.repositories.credit_cards import CreditCardRepositoryProtocol
from finance_api.repositories.imports import ImportBatchRepositoryProtocol
from finance_api.schemas.imports import (
    ImportBatchResponse,
    PossibleDuplicateInfo,
    StagedTransactionResponse,
)
from finance_api.services.incomes import IncomeService
from finance_api.services.spents import SpentService


class ImportBatchPresenter:
    """Builds import batch and staged transaction responses."""

    def __init__(
        self,
        batch_repo: ImportBatchRepositoryProtocol,
        account_repo: AccountRepositoryProtocol,
        credit_card_repo: CreditCardRepositoryProtocol,
        spent_service: SpentService,
        income_service: IncomeService,
    ) -> None:
        self._batch_repo = batch_repo
        self._account_repo = account_repo
        self._credit_card_repo = credit_card_repo
        self._spent_service = spent_service
        self._income_service = income_service

    def build_batch_response(
        self,
        batch: ImportBatch,
        target: ResolvedImportTarget,
        counts: dict[str, int],
    ) -> ImportBatchResponse:
        response = ImportBatchResponse.model_validate(batch)
        response.account_name = target.target_name
        if target.credit_card_id:
            response.credit_card_id = target.credit_card_id
            response.credit_card_name = target.target_name
        response.counts = counts
        return response

    async def build_batch_list(self, batches: list[ImportBatch]) -> list[ImportBatchResponse]:
        return [await self._build_listed_batch(batch) for batch in batches]

    async def _build_listed_batch(self, batch: ImportBatch) -> ImportBatchResponse:
        response = ImportBatchResponse.model_validate(batch)
        await self._apply_account_name(batch, response)
        await self._apply_credit_card_name(batch, response)
        response.counts = await self._batch_repo.get_counts_by_status(batch.id)
        return response

    async def _apply_account_name(
        self,
        batch: ImportBatch,
        response: ImportBatchResponse,
    ) -> None:
        if not batch.account_id:
            return
        account = await self._account_repo.get_by_id(batch.account_id)
        response.account_name = account.name if account else None

    async def _apply_credit_card_name(
        self,
        batch: ImportBatch,
        response: ImportBatchResponse,
    ) -> None:
        if not batch.credit_card_id:
            return
        card = await self._credit_card_repo.get_by_id(batch.credit_card_id)
        if not card:
            return
        response.credit_card_id = card.id
        response.credit_card_name = card.name
        if not response.account_name:
            response.account_name = card.name

    async def to_tx_response(self, tx: StagedTransaction) -> StagedTransactionResponse:
        response = StagedTransactionResponse.model_validate(tx)
        response.amount = tx.amount
        response.confidence = float(tx.confidence) if tx.confidence is not None else None
        response.current_installment = tx.current_installment
        response.total_installments = tx.total_installments
        response.card_last_digits = tx.card_last_digits

        duplicate = await self._resolve_duplicate(tx)
        if duplicate:
            response.possible_duplicate = duplicate
        return response

    async def _resolve_duplicate(self, tx: StagedTransaction) -> PossibleDuplicateInfo | None:
        if tx.possible_duplicate_of_spent_id:
            return await self._build_spent_duplicate(tx.possible_duplicate_of_spent_id)
        if tx.possible_duplicate_of_income_id:
            return await self._build_income_duplicate(tx.possible_duplicate_of_income_id)
        return None

    async def _build_spent_duplicate(self, spent_id: UUID) -> PossibleDuplicateInfo | None:
        spent = await self._spent_service.repo.get_by_id(spent_id)
        if not spent:
            return None
        return PossibleDuplicateInfo(
            type="spent",
            id=spent.id,
            label=spent.item_bought,
            amount=Decimal(str(spent.amount)),
            date=spent.created_at.date(),
        )

    async def _build_income_duplicate(self, income_id: UUID) -> PossibleDuplicateInfo | None:
        income = await self._income_service.repo.get_by_id(income_id)
        if not income:
            return None
        return PossibleDuplicateInfo(
            type="income",
            id=income.id,
            label=income.description,
            amount=Decimal(str(income.amount)),
            date=income.received_at.date(),
        )
