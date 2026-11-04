"""Structural contracts for the import feature (bulk actions, commit, duplicates)."""

from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.schemas.imports import (
    BulkActionRequest,
    CommitContext,
    CommitStepOutcome,
    StepOutcome,
)


class BulkActionStrategy(Protocol):
    """Structural contract for executing a bulk action on a StagedTransaction."""

    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome: ...


class TransactionCommitStrategy(Protocol):
    """Structural contract for committing an approved StagedTransaction."""

    async def commit(
        self,
        tx: StagedTransaction,
        ctx: CommitContext,
    ) -> CommitStepOutcome: ...


class DuplicateDetectorStrategy(Protocol):
    """Structural contract for detecting possible duplicates of a staged row."""

    async def detect(
        self,
        tx_repo: StagedTransactionRepository,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        amount: Decimal,
        tx_date: date,
    ) -> tuple[UUID | None, UUID | None]: ...
