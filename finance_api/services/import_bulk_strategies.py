"""Bulk action strategies applied to staged import rows (approve, ignore, reopen, set category)."""

from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.category_rules import CategoryRuleRepositoryProtocol
from finance_api.schemas.enums import BulkActionType, StepOutcomeStatus, TransactionKind
from finance_api.schemas.imports import BulkActionRequest, StepOutcome
from finance_api.services.protocols import (
    BulkActionStrategy,
    CategoryLookupProtocol,
    IncomeCategoryLookupProtocol,
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
        self._repositories_by_kind: dict[
            TransactionKind,
            CategoryLookupProtocol | IncomeCategoryLookupProtocol,
        ] = {
            TransactionKind.EXPENSE: category_repo,
            TransactionKind.INCOME: income_category_repo,
        }
        self._rule_repo = rule_repo

    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome:
        if not req.category:
            return StepOutcome(status=StepOutcomeStatus.SKIPPED)

        clean_category = req.category.strip().lower()

        repository = self._repositories_by_kind.get(tx.kind)
        if repository is not None and not await repository.get_by_key(clean_category):
            return StepOutcome(
                status=StepOutcomeStatus.ERROR,
                error_message=f"Categoria '{clean_category}' não existe",
            )

        tx.category = clean_category
        if tx.status == "PENDING":
            tx.status = "APPROVED"

        await self._learn_rule(tx, req)
        return StepOutcome(status=StepOutcomeStatus.UPDATED)

    async def _learn_rule(self, tx: StagedTransaction, req: BulkActionRequest) -> None:
        """Learns the merchant->category rule when the request asks for it."""
        if not req.remember or not tx.merchant:
            return

        await self._rule_repo.upsert_rule(
            pattern=tx.merchant,
            direction=tx.direction,
            kind=tx.kind,
            category=tx.category,
            source="LEARNED",
        )


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
