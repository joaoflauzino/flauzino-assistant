"""Repository contracts for finance_api persistence.

This module declares only structural contracts (Protocols). The concrete
SQLAlchemy implementations live in their feature modules and satisfy these
contracts structurally, without inheriting from them. Services must depend on
the contracts declared here, never on the concrete repositories.
"""

import builtins
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from finance_api.models.accounts import Account
from finance_api.models.categories import Category
from finance_api.models.category_rules import CategoryRule
from finance_api.models.credit_cards import CreditCard
from finance_api.models.import_batches import ImportBatch
from finance_api.models.income_categories import IncomeCategory
from finance_api.models.incomes import Income
from finance_api.models.invoices import Invoice
from finance_api.models.limits import SpendingLimit
from finance_api.models.payment_methods import PaymentMethod
from finance_api.models.spents import Spent
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.models.subscriptions import Subscription
from finance_api.schemas.accounts import AccountCreate, AccountUpdate
from finance_api.schemas.categories import CategoryCreate, CategoryUpdate
from finance_api.schemas.credit_cards import CreditCardCreate, CreditCardUpdate
from finance_api.schemas.income_categories import IncomeCategoryCreate, IncomeCategoryUpdate
from finance_api.schemas.incomes import IncomeCreate, IncomeUpdate
from finance_api.schemas.installments import InstallmentSummaryRow
from finance_api.schemas.invoices import InvoiceCreate, InvoiceUpdate
from finance_api.schemas.limits import SpendingLimitCreate, SpendingLimitUpdate
from finance_api.schemas.payment_methods import PaymentMethodCreate, PaymentMethodUpdate
from finance_api.schemas.spents import SpentCreate, SpentUpdate
from finance_api.schemas.subscriptions import SubscriptionCreate, SubscriptionUpdate


class RepositoryProtocol[T, ID](Protocol):
    """Structural contract for any entity repository (PEP 695 Generic Protocol)."""

    async def get_by_id(self, entity_id: ID) -> T | None: ...


class AccountLookupProtocol(Protocol):
    """Narrow account lookup contract for services that only validate links."""

    async def get_by_id(self, account_id: UUID) -> Account | None: ...


class AccountRepositoryProtocol(RepositoryProtocol[Account, UUID], Protocol):
    """Domain repository contract for Account persistence."""

    async def get_by_key(self, key: str) -> Account | None: ...
    async def list(
        self, page: int = 1, size: int = 100, owner: str | None = None
    ) -> tuple[Sequence[Account], int]: ...
    async def create(self, account_data: AccountCreate) -> Account: ...
    async def update(self, account_id: UUID, update_data: AccountUpdate) -> Account | None: ...
    async def delete(self, account_id: UUID) -> bool: ...


class CreditCardRepositoryProtocol(RepositoryProtocol[CreditCard, UUID], Protocol):
    """Domain repository contract for CreditCard persistence."""

    async def get_by_key(self, key: str) -> CreditCard | None: ...
    async def list(
        self, page: int = 1, size: int = 100, account_id: UUID | None = None
    ) -> tuple[Sequence[CreditCard], int]: ...
    async def create(self, card_data: CreditCardCreate) -> CreditCard: ...
    async def update(self, card_id: UUID, update_data: CreditCardUpdate) -> CreditCard | None: ...
    async def delete(self, card_id: UUID) -> bool: ...


class CategoryRepositoryProtocol(RepositoryProtocol[Category, UUID], Protocol):
    """Domain repository contract for Category persistence."""

    async def list(self, skip: int = 0, limit: int = 100) -> tuple[Sequence[Category], int]: ...
    async def get_by_key(self, key: str) -> Category | None: ...
    async def create(self, category_data: CategoryCreate) -> Category: ...
    async def update(self, category_id: UUID, update_data: CategoryUpdate) -> Category | None: ...
    async def delete(self, category_id: UUID) -> bool: ...


class IncomeCategoryRepositoryProtocol(RepositoryProtocol[IncomeCategory, UUID], Protocol):
    """Domain repository contract for IncomeCategory persistence."""

    async def list(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[Sequence[IncomeCategory], int]: ...
    async def get_by_key(self, key: str) -> IncomeCategory | None: ...
    async def create(self, category_data: IncomeCategoryCreate) -> IncomeCategory: ...
    async def update(
        self, category_id: UUID, update_data: IncomeCategoryUpdate
    ) -> IncomeCategory | None: ...
    async def delete(self, category_id: UUID) -> bool: ...


class IncomeRepositoryProtocol(RepositoryProtocol[Income, UUID], Protocol):
    """Domain repository contract for Income persistence."""

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
        category: str | None = None,
    ) -> tuple[Sequence[Income], int]: ...
    async def list_by_period(self, start_date: date, end_date: date) -> Sequence[Income]: ...
    async def create(self, income_data: IncomeCreate) -> Income: ...
    async def update(self, income_id: UUID, update_data: IncomeUpdate) -> Income | None: ...
    async def delete(self, income_id: UUID) -> bool: ...


class InvoiceRepositoryProtocol(Protocol):
    """Domain repository contract for Invoice persistence."""

    async def create(self, invoice: InvoiceCreate) -> Invoice: ...
    async def get_by_payment_method_and_month(
        self, payment_method_key: str, reference_month: str
    ) -> Invoice | None: ...
    async def list_by_month(self, reference_month: str) -> Sequence[Invoice]: ...
    async def update(self, invoice_id: UUID, update_data: InvoiceUpdate) -> Invoice | None: ...


class SpendingLimitRepositoryProtocol(RepositoryProtocol[SpendingLimit, UUID], Protocol):
    """Domain repository contract for SpendingLimit persistence."""

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[Sequence[SpendingLimit], int]: ...
    async def get_by_category(self, category: str) -> SpendingLimit | None: ...
    async def create(self, limit_data: SpendingLimitCreate) -> SpendingLimit: ...
    async def update(
        self, limit_id: UUID, update_data: SpendingLimitUpdate
    ) -> SpendingLimit | None: ...
    async def delete(self, limit_id: UUID) -> bool: ...


class PaymentMethodRepositoryProtocol(RepositoryProtocol[PaymentMethod, UUID], Protocol):
    """Domain repository contract for PaymentMethod persistence."""

    async def get_by_key(self, key: str) -> PaymentMethod | None: ...
    async def list(self, page: int = 1, size: int = 100) -> tuple[Sequence[PaymentMethod], int]: ...
    async def list_credit_cards(self) -> Sequence[PaymentMethod]: ...
    async def create(self, method_data: PaymentMethodCreate) -> PaymentMethod: ...
    async def update(
        self, method_id: UUID, update_data: PaymentMethodUpdate
    ) -> PaymentMethod | None: ...
    async def delete(self, method_id: UUID) -> bool: ...


class SpentRepositoryProtocol(RepositoryProtocol[Spent, UUID], Protocol):
    """Domain repository contract for Spent persistence."""

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[Sequence[Spent], int]: ...
    async def list_by_multiple_periods(
        self,
        periods: builtins.list[tuple[str, date, date]],
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Spent], int]: ...
    async def create(self, spent: SpentCreate) -> Spent: ...
    async def create_many(self, spents: builtins.list[Spent]) -> Sequence[Spent]: ...
    async def get_installments_summary(self) -> Sequence[InstallmentSummaryRow]: ...
    async def update(self, spent_id: UUID, update_data: SpentUpdate) -> Spent | None: ...
    async def delete(self, spent_id: UUID) -> bool: ...


class StagedTransactionRepositoryProtocol(RepositoryProtocol[StagedTransaction, UUID], Protocol):
    """Domain repository contract for StagedTransaction persistence."""

    async def get_existing_fingerprints(self, fps: builtins.list[str]) -> set[str]: ...
    async def create_many(
        self, transactions: builtins.list[StagedTransaction]
    ) -> Sequence[StagedTransaction]: ...
    async def save(self, tx: StagedTransaction) -> StagedTransaction: ...
    async def find_possible_duplicate_spent(
        self,
        account_id: UUID | None,
        amount: Decimal,
        tx_date: date,
        credit_card_id: UUID | None = None,
        tolerance_days: int = 3,
    ) -> Spent | None: ...
    async def find_possible_duplicate_income(
        self,
        account_id: UUID | None,
        amount: Decimal,
        tx_date: date,
        tolerance_days: int = 3,
    ) -> Income | None: ...
    async def list_by_filter(
        self,
        batch_id: UUID | None = None,
        status: str | None = None,
        kind: str | None = None,
        only_duplicates: bool = False,
        only_unclassified: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> tuple[Sequence[StagedTransaction], int]: ...
    async def get_approved_for_commit(
        self, batch_id: UUID | None = None
    ) -> Sequence[StagedTransaction]: ...
    async def list_for_reclassification(
        self, batch_id: UUID | None = None
    ) -> Sequence[StagedTransaction]: ...


class SubscriptionRepositoryProtocol(RepositoryProtocol[Subscription, UUID], Protocol):
    """Domain repository contract for Subscription persistence."""

    async def list(
        self, skip: int = 0, limit: int = 100, active_only: bool = False
    ) -> tuple[Sequence[Subscription], int]: ...
    async def create(self, subscription: SubscriptionCreate) -> Subscription: ...
    async def update(
        self, subscription_id: UUID, update_data: SubscriptionUpdate
    ) -> Subscription | None: ...
    async def delete(self, subscription_id: UUID) -> bool: ...


class CategoryRuleRepositoryProtocol(Protocol):
    """Domain repository contract for CategoryRule persistence."""

    async def list_all(self) -> Sequence[CategoryRule]: ...
    async def find_matching_rule(self, merchant: str, direction: str) -> CategoryRule | None: ...
    async def increment_hits(self, rule_id: UUID) -> None: ...
    async def upsert_rule(
        self,
        pattern: str,
        direction: str,
        kind: str,
        category: str | None,
        source: str = "LEARNED",
    ) -> CategoryRule: ...
    async def delete_by_id(self, rule_id: UUID) -> bool: ...


class ImportBatchRepositoryProtocol(RepositoryProtocol[ImportBatch, UUID], Protocol):
    """Domain repository contract for ImportBatch persistence."""

    async def create(self, batch: ImportBatch) -> ImportBatch: ...
    async def update_batch_stats(
        self, batch: ImportBatch, possible_duplicates: int, ai_used: bool
    ) -> ImportBatch: ...
    async def get_by_sha256(self, sha256_hash: str) -> ImportBatch | None: ...
    async def list_all(self, limit: int = 50, offset: int = 0) -> Sequence[ImportBatch]: ...
    async def get_counts_by_status(self, batch_id: UUID) -> dict[str, int]: ...
    async def get_global_summary(self) -> dict[str, int]: ...
