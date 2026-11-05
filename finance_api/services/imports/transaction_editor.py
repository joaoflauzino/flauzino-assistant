"""Field-level mutations applied to staged transactions before they are committed."""

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any
from uuid import UUID

from finance_api.core.exceptions import EntityNotFoundError, ValidationError
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.protocols import (
    CategoryRepositoryProtocol,
    CategoryRuleRepositoryProtocol,
    IncomeCategoryRepositoryProtocol,
    StagedTransactionRepositoryProtocol,
)
from finance_api.schemas.imports import StagedTransactionResponse, StagedTransactionUpdate
from finance_api.services.imports.presenter import ImportBatchPresenter

ALLOWED_KINDS = ("EXPENSE", "INCOME", "TRANSFER", "INVOICE_PAYMENT", "REFUND")
CATEGORYLESS_KINDS = ("TRANSFER", "INVOICE_PAYMENT", "REFUND")
CATEGORY_REQUIRED_KINDS = ("EXPENSE", "INCOME")
LEARNABLE_KINDS = ("EXPENSE", "INCOME")
ALLOWED_STATUSES = ("PENDING", "APPROVED", "IGNORED")
COMMITTED_STATUS = "COMMITTED"
APPROVED_STATUS = "APPROVED"
LINKED_STATUS = "LINKED"

FieldApplier = Callable[[StagedTransaction, Any], Awaitable[None]]


class StagedTransactionEditor:
    """Applies user edits and duplicate links to staged transactions."""

    def __init__(
        self,
        tx_repo: StagedTransactionRepositoryProtocol,
        rule_repo: CategoryRuleRepositoryProtocol,
        category_repo: CategoryRepositoryProtocol,
        income_category_repo: IncomeCategoryRepositoryProtocol,
        presenter: ImportBatchPresenter,
    ) -> None:
        self._tx_repo = tx_repo
        self._rule_repo = rule_repo
        self._category_repo = category_repo
        self._income_category_repo = income_category_repo
        self._presenter = presenter
        self._category_validators: dict[str, Callable[[str], Awaitable[None]]] = {
            "EXPENSE": self._require_expense_category,
            "INCOME": self._require_income_category,
        }

    async def update(
        self,
        tx_id: UUID,
        data: StagedTransactionUpdate,
    ) -> StagedTransactionResponse:
        """Applies every provided field of ``data`` and persists the transaction."""
        tx = await self._get_editable(tx_id)
        patch = data.model_dump(exclude_none=True)

        for field, value in patch.items():
            applier = self._appliers().get(field)
            if applier is None:
                continue
            await applier(tx, value)

        await self._learn_rule(tx, data.remember)
        saved = await self._tx_repo.save(tx)
        return await self._presenter.to_tx_response(saved)

    async def link(self, tx_id: UUID) -> StagedTransactionResponse:
        """Marks the transaction as linked to the duplicate it points to."""
        tx = await self._tx_repo.get_by_id(tx_id)
        if not tx:
            raise EntityNotFoundError(f"Transação {tx_id} não encontrada")
        if not tx.possible_duplicate_of_spent_id and not tx.possible_duplicate_of_income_id:
            raise ValidationError("Esta transação não possui duplicata identificada para vincular.")

        self._apply_duplicate_link(tx)
        tx.status = LINKED_STATUS
        saved = await self._tx_repo.save(tx)
        return await self._presenter.to_tx_response(saved)

    async def _get_editable(self, tx_id: UUID) -> StagedTransaction:
        tx = await self._tx_repo.get_by_id(tx_id)
        if not tx:
            raise EntityNotFoundError(f"Transação {tx_id} não encontrada")
        if tx.status == COMMITTED_STATUS:
            raise ValidationError("Transação já foi efetivada e não pode ser alterada.")
        return tx

    def _appliers(self) -> dict[str, FieldApplier]:
        return {
            "kind": self._apply_kind,
            "description": self._apply_description,
            "location": self._apply_location,
            "competence_date": self._apply_competence_date,
            "category": self._apply_category,
            "status": self._apply_status,
        }

    async def _apply_kind(self, tx: StagedTransaction, kind: str) -> None:
        if kind not in ALLOWED_KINDS:
            raise ValidationError(f"Tipo '{kind}' inválido.")
        tx.kind = kind
        if kind in CATEGORYLESS_KINDS:
            tx.category = None

    async def _apply_description(self, tx: StagedTransaction, description: str) -> None:
        tx.description = description.strip()[:50]

    async def _apply_location(self, tx: StagedTransaction, location: str) -> None:
        tx.location = location.strip() or None

    async def _apply_competence_date(self, tx: StagedTransaction, competence_date: date) -> None:
        tx.competence_date = competence_date

    async def _apply_category(self, tx: StagedTransaction, category: str) -> None:
        clean_category = category.strip().lower() or None
        if clean_category:
            await self._validate_category(tx.kind, clean_category)
        tx.category = clean_category

    async def _apply_status(self, tx: StagedTransaction, status: str) -> None:
        if status not in ALLOWED_STATUSES:
            raise ValidationError(f"Status '{status}' inválido para transição direta.")
        self._ensure_approvable(tx, status)
        tx.status = status

    def _ensure_approvable(self, tx: StagedTransaction, status: str) -> None:
        if status != APPROVED_STATUS:
            return
        if tx.kind in CATEGORY_REQUIRED_KINDS and not tx.category:
            raise ValidationError(
                f"Selecione uma categoria para aprovar uma transação do tipo {tx.kind}."
            )

    async def _validate_category(self, kind: str, category_key: str) -> None:
        validator = self._category_validators.get(kind)
        if validator:
            await validator(category_key)

    async def _require_expense_category(self, category_key: str) -> None:
        category = await self._category_repo.get_by_key(category_key)
        if not category:
            raise ValidationError(f"Categoria de despesa '{category_key}' não existe.")

    async def _require_income_category(self, category_key: str) -> None:
        category = await self._income_category_repo.get_by_key(category_key)
        if not category:
            raise ValidationError(f"Categoria de receita '{category_key}' não existe.")

    async def _learn_rule(self, tx: StagedTransaction, remember: bool) -> None:
        if not remember:
            return
        if not (tx.category and tx.merchant and tx.kind in LEARNABLE_KINDS):
            return
        await self._rule_repo.upsert_rule(
            pattern=tx.merchant,
            direction=tx.direction,
            kind=tx.kind,
            category=tx.category,
            source="LEARNED",
        )

    def _apply_duplicate_link(self, tx: StagedTransaction) -> None:
        if tx.possible_duplicate_of_spent_id:
            tx.committed_spent_id = tx.possible_duplicate_of_spent_id
        if tx.possible_duplicate_of_income_id:
            tx.committed_income_id = tx.possible_duplicate_of_income_id
