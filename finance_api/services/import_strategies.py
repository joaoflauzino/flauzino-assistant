"""Strategy Pattern implementations for bulk actions and commit workflows in ImportService."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.category_rules import CategoryRuleRepositoryProtocol
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.schemas.enums import (
    BulkActionType,
    CommitOutcomeStatus,
    StepOutcomeStatus,
    TransactionKind,
)
from finance_api.schemas.imports import (
    BulkActionRequest,
    CommitContext,
    CommitStepOutcome,
    StepOutcome,
)
from finance_api.schemas.incomes import IncomeCreate
from finance_api.schemas.spents import SpentCreate
from finance_api.services.incomes import IncomeService
from finance_api.services.protocols import (
    BulkActionStrategy,
    CategoryLookupProtocol,
    IncomeCategoryLookupProtocol,
    TransactionCommitStrategy,
)
from finance_api.services.spents import SpentService

SALARY_KEYWORDS: tuple[str, ...] = (
    "SALARIO",
    "SALÁRIO",
    "FOLHA",
    "PRO-LABORE",
    "REMUNERACAO",
    "VENCIMENTO",
    "PPR",
    "PLR",
)


class ApproveBulkStrategy:
    """Approves a staged transaction if it has no duplicate flags and has a category when required."""

    def __init__(self, rule_repo: CategoryRuleRepositoryProtocol) -> None:
        self._rule_repo = rule_repo

    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome:
        if tx.possible_duplicate_of_spent_id or tx.possible_duplicate_of_income_id:
            return StepOutcome(status=StepOutcomeStatus.SKIPPED)
        if tx.kind in (TransactionKind.EXPENSE, TransactionKind.INCOME) and not tx.category:
            return StepOutcome(status=StepOutcomeStatus.SKIPPED)

        tx.status = "APPROVED"
        if req.remember and tx.category and tx.merchant:
            await self._rule_repo.upsert_rule(
                pattern=tx.merchant,
                direction=tx.direction,
                kind=tx.kind,
                category=tx.category,
                source="LEARNED",
            )
        return StepOutcome(status=StepOutcomeStatus.UPDATED)


class IgnoreBulkStrategy:
    """Marks a staged transaction as IGNORED."""

    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome:
        tx.status = "IGNORED"
        return StepOutcome(status=StepOutcomeStatus.UPDATED)


class ReopenBulkStrategy:
    """Reopens a staged transaction back to PENDING if not COMMITTED."""

    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome:
        if tx.status == "COMMITTED":
            return StepOutcome(status=StepOutcomeStatus.SKIPPED)
        tx.status = "PENDING"
        return StepOutcome(status=StepOutcomeStatus.UPDATED)


class SetCategoryBulkStrategy:
    """Updates the category of a staged transaction with kind-aware validation and rule learning."""

    def __init__(
        self,
        category_repo: CategoryLookupProtocol,
        income_category_repo: IncomeCategoryLookupProtocol,
        rule_repo: CategoryRuleRepositoryProtocol,
    ) -> None:
        self._category_repo = category_repo
        self._income_category_repo = income_category_repo
        self._rule_repo = rule_repo

    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome:
        if not req.category:
            return StepOutcome(status=StepOutcomeStatus.SKIPPED)

        clean_cat = req.category.strip().lower()

        if tx.kind == TransactionKind.EXPENSE and not await self._category_repo.get_by_key(
            clean_cat
        ):
            return StepOutcome(
                status=StepOutcomeStatus.ERROR,
                error_message=f"Categoria '{clean_cat}' não existe",
            )
        if tx.kind == TransactionKind.INCOME and not await self._income_category_repo.get_by_key(
            clean_cat
        ):
            return StepOutcome(
                status=StepOutcomeStatus.ERROR,
                error_message=f"Categoria '{clean_cat}' não existe",
            )

        tx.category = clean_cat
        if tx.status == "PENDING":
            tx.status = "APPROVED"

        if req.remember and tx.merchant:
            await self._rule_repo.upsert_rule(
                pattern=tx.merchant,
                direction=tx.direction,
                kind=tx.kind,
                category=tx.category,
                source="LEARNED",
            )
        return StepOutcome(status=StepOutcomeStatus.UPDATED)


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
            amount=tx.amount,
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
            amount=tx.amount,
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


class DuplicateDetectorStrategy(Protocol):
    """Protocol for duplicate detection strategies."""

    async def detect(
        self,
        tx_repo: StagedTransactionRepository,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        amount: Decimal,
        tx_date: date,
    ) -> tuple[UUID | None, UUID | None]: ...


class ExpenseDuplicateDetector:
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


class NullDuplicateDetector:
    async def detect(
        self,
        tx_repo: StagedTransactionRepository,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        amount: Decimal,
        tx_date: date,
    ) -> tuple[UUID | None, UUID | None]:
        return (None, None)


def build_default_duplicate_detectors() -> dict[str, DuplicateDetectorStrategy]:
    return {
        TransactionKind.EXPENSE: ExpenseDuplicateDetector(),
        TransactionKind.INCOME: IncomeDuplicateDetector(),
    }


def resolve_salary_competence_date(
    kind: str,
    occurred_at: datetime,
    raw_title: str,
    raw_description: str | None,
) -> date | None:
    """Resolves competence date for salary-like income arriving within the first week of month."""
    if kind != TransactionKind.INCOME:
        return None
    tx_dt = occurred_at.date()
    norm_raw = f"{raw_title} {raw_description or ''}".upper()
    if any(k in norm_raw for k in SALARY_KEYWORDS) and tx_dt.day <= 7:
        first_of_month = tx_dt.replace(day=1)
        return first_of_month - timedelta(days=1)
    return tx_dt


def build_default_bulk_strategies(
    rule_repo: CategoryRuleRepositoryProtocol,
    category_repo: CategoryLookupProtocol,
    income_category_repo: IncomeCategoryLookupProtocol,
) -> dict[str, BulkActionStrategy]:
    """Builds the default dispatch table mapping BulkActionType to concrete strategies."""
    return {
        BulkActionType.APPROVE: ApproveBulkStrategy(rule_repo=rule_repo),
        BulkActionType.IGNORE: IgnoreBulkStrategy(),
        BulkActionType.REOPEN: ReopenBulkStrategy(),
        BulkActionType.SET_CATEGORY: SetCategoryBulkStrategy(
            category_repo=category_repo,
            income_category_repo=income_category_repo,
            rule_repo=rule_repo,
        ),
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
