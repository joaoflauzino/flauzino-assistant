"""Commit strategies and duplicate detectors for staged import rows."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.schemas.enums import CommitOutcomeStatus, TransactionKind
from finance_api.schemas.imports import CommitContext, CommitStepOutcome
from finance_api.schemas.incomes import IncomeCreate
from finance_api.schemas.spents import SpentCreate
from finance_api.services.incomes import IncomeService
from finance_api.services.protocols import DuplicateDetectorStrategy, TransactionCommitStrategy
from finance_api.services.spents import SpentService


class ExpenseCommitStrategy:
    """Commits an EXPENSE transaction into a real Spent record."""

    def __init__(self, spent_service: SpentService) -> None:
        self._spent_service = spent_service

    async def commit(
        self,
        tx: StagedTransaction,
        ctx: CommitContext,
    ) -> CommitStepOutcome:
        if not tx.category:
            return CommitStepOutcome(
                status=CommitOutcomeStatus.FAILED,
                error_message="Despesa sem categoria",
            )

        spent_data = SpentCreate(
            category=tx.category,
            amount=float(tx.amount),
            item_bought=tx.description[:50],
            payment_method=ctx.payment_method_key,
            payment_type=ctx.payment_type_value,
            account_id=ctx.account_id,
            credit_card_id=tx.credit_card_id,
            location=tx.location,
            created_at=tx.occurred_at,
            is_installment=False,
            current_installment=tx.current_installment,
            total_installments=tx.total_installments,
        )
        created_spent = await self._spent_service.create(spent_data)
        tx.committed_spent_id = created_spent.id
        tx.status = "COMMITTED"
        return CommitStepOutcome(status=CommitOutcomeStatus.COMMITTED_SPENT)


class IncomeCommitStrategy:
    """Commits an INCOME transaction into a real Income record."""

    def __init__(self, income_service: IncomeService) -> None:
        self._income_service = income_service

    async def commit(
        self,
        tx: StagedTransaction,
        ctx: CommitContext,
    ) -> CommitStepOutcome:
        if not tx.category:
            return CommitStepOutcome(
                status=CommitOutcomeStatus.FAILED,
                error_message="Receita sem categoria",
            )

        income_data = IncomeCreate(
            description=tx.description[:100],
            amount=float(tx.amount),
            category=tx.category,
            payment_method=ctx.payment_method_key,
            account_id=ctx.account_id,
            received_at=tx.occurred_at,
            competence_date=tx.competence_date or tx.occurred_at.date(),
        )
        created_income = await self._income_service.create(income_data)
        tx.committed_income_id = created_income.id
        tx.status = "COMMITTED"
        return CommitStepOutcome(status=CommitOutcomeStatus.COMMITTED_INCOME)


class NonRecordCommitStrategy:
    """Commits TRANSFER, INVOICE_PAYMENT, and REFUND transactions without creating duplicate records."""

    async def commit(
        self,
        tx: StagedTransaction,
        ctx: CommitContext,
    ) -> CommitStepOutcome:
        tx.status = "COMMITTED"
        return CommitStepOutcome(status=CommitOutcomeStatus.PROCESSED_WITHOUT_RECORD)


class ExpenseDuplicateDetector:
    """Finds a possible duplicate spent for an EXPENSE staged row."""

    async def detect(
        self,
        tx_repo: StagedTransactionRepository,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        amount: Decimal,
        tx_date: date,
    ) -> tuple[UUID | None, UUID | None]:
        match = await tx_repo.find_possible_duplicate_spent(
            account_id=account_id,
            amount=amount,
            tx_date=tx_date,
            credit_card_id=credit_card_id,
        )
        return (match.id if match else None, None)


class IncomeDuplicateDetector:
    """Finds a possible duplicate income for an INCOME staged row."""

    async def detect(
        self,
        tx_repo: StagedTransactionRepository,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        amount: Decimal,
        tx_date: date,
    ) -> tuple[UUID | None, UUID | None]:
        match = await tx_repo.find_possible_duplicate_income(
            account_id=account_id,
            amount=amount,
            tx_date=tx_date,
        )
        return (None, match.id if match else None)


def build_default_duplicate_detectors() -> dict[str, DuplicateDetectorStrategy]:
    """Builds the default dispatch table mapping TransactionKind to duplicate detectors."""
    return {
        TransactionKind.EXPENSE: ExpenseDuplicateDetector(),
        TransactionKind.INCOME: IncomeDuplicateDetector(),
    }


def build_default_commit_strategies(
    spent_service: SpentService,
    income_service: IncomeService,
) -> dict[str, TransactionCommitStrategy]:
    """Builds the default dispatch table mapping TransactionKind to commit strategies."""
    non_record_strategy = NonRecordCommitStrategy()
    return {
        TransactionKind.EXPENSE: ExpenseCommitStrategy(spent_service=spent_service),
        TransactionKind.INCOME: IncomeCommitStrategy(income_service=income_service),
        TransactionKind.TRANSFER: non_record_strategy,
        TransactionKind.INVOICE_PAYMENT: non_record_strategy,
        TransactionKind.REFUND: non_record_strategy,
    }
