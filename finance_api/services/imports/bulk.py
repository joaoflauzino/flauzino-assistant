"""Bulk action execution over staged transactions."""

from uuid import UUID

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.schemas.enums import StepOutcomeStatus
from finance_api.schemas.imports import (
    BulkActionError,
    BulkActionRequest,
    BulkActionResult,
    StepOutcome,
)
from finance_api.services.protocols import BulkActionStrategy

type BulkStepResult = tuple[StepOutcomeStatus, BulkActionError | None]


class ImportBulkService:
    """Applies a bulk action strategy to a list of staged transaction ids."""

    def __init__(
        self,
        tx_repo: StagedTransactionRepository,
        bulk_strategies: dict[str, BulkActionStrategy],
    ) -> None:
        self._tx_repo = tx_repo
        self._bulk_strategies = bulk_strategies

    async def execute(self, req: BulkActionRequest) -> BulkActionResult:
        strategy = self._bulk_strategies.get(str(req.action))
        updated = 0
        skipped = 0
        errors: list[BulkActionError] = []

        for tx_id in req.ids:
            status, error = await self._process_one(tx_id, strategy, req)
            if error:
                errors.append(error)
            elif status == StepOutcomeStatus.SKIPPED:
                skipped += 1
            else:
                updated += 1

        return BulkActionResult(updated=updated, skipped=skipped, errors=errors)

    async def _process_one(
        self,
        tx_id: UUID,
        strategy: BulkActionStrategy | None,
        req: BulkActionRequest,
    ) -> BulkStepResult:
        tx = await self._tx_repo.get_by_id(tx_id)
        if not tx:
            return self._error(tx_id, "Transação não encontrada")
        if tx.status == "COMMITTED":
            return StepOutcomeStatus.SKIPPED, None
        if strategy is None:
            return self._error(tx_id, f"Ação desconhecida: {req.action}")
        return await self._execute_strategy(tx, strategy, req)

    async def _execute_strategy(
        self,
        tx: StagedTransaction,
        strategy: BulkActionStrategy,
        req: BulkActionRequest,
    ) -> BulkStepResult:
        try:
            outcome: StepOutcome = await strategy.execute(tx, req)
        except Exception as error:
            return self._error(tx.id, str(error))

        if outcome.status == StepOutcomeStatus.ERROR:
            return self._error(tx.id, outcome.error_message or "Erro na validação da ação")

        if outcome.status == StepOutcomeStatus.SKIPPED:
            return StepOutcomeStatus.SKIPPED, None

        await self._tx_repo.save(tx)
        return StepOutcomeStatus.UPDATED, None

    def _error(self, tx_id: UUID, message: str) -> BulkStepResult:
        return StepOutcomeStatus.ERROR, BulkActionError(id=tx_id, error=message)
