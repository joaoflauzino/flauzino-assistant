"""Wiring and structural-substitution checks for the repository contracts.

The structural conformance of every concrete repository with its Protocol is
also enforced statically (``mypy`` checks the provider return annotations).
These tests protect the runtime side: providers must expose the concrete
implementations and services must accept any structural implementation.
"""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from finance_api.core.composition import (
    build_account_service,
    build_balance_service,
    build_category_service,
    build_credit_card_service,
    build_income_service,
    build_payment_method_service,
    build_spent_service,
)
from finance_api.core.dependencies import (
    get_account_repository,
    get_category_repository,
    get_category_rule_repository,
    get_credit_card_repository,
    get_import_batch_repository,
    get_income_category_repository,
    get_income_repository,
    get_invoice_repository,
    get_payment_method_repository,
    get_spending_limit_repository,
    get_spent_repository,
    get_staged_transaction_repository,
)
from finance_api.models.categories import Category
from finance_api.repositories.accounts import AccountRepository
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.category_rules import CategoryRuleRepository
from finance_api.repositories.credit_cards import CreditCardRepository
from finance_api.repositories.imports import ImportBatchRepository
from finance_api.repositories.income_categories import IncomeCategoryRepository
from finance_api.repositories.incomes import IncomeRepository
from finance_api.repositories.invoices import InvoiceRepository
from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.repositories.spents import SpentRepository
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.schemas.categories import CategoryCreate, CategoryUpdate
from finance_api.services.categories import CategoryService


def test_repository_providers_return_concrete_implementations() -> None:
    db = MagicMock()

    assert isinstance(get_account_repository(db), AccountRepository)
    assert isinstance(get_credit_card_repository(db), CreditCardRepository)
    assert isinstance(get_category_repository(db), CategoryRepository)
    assert isinstance(get_income_category_repository(db), IncomeCategoryRepository)
    assert isinstance(get_payment_method_repository(db), PaymentMethodRepository)
    assert isinstance(get_invoice_repository(db), InvoiceRepository)
    assert isinstance(get_spent_repository(db), SpentRepository)
    assert isinstance(get_income_repository(db), IncomeRepository)
    assert isinstance(get_spending_limit_repository(db), SpendingLimitRepository)
    assert isinstance(get_category_rule_repository(db), CategoryRuleRepository)
    assert isinstance(get_import_batch_repository(db), ImportBatchRepository)
    assert isinstance(get_staged_transaction_repository(db), StagedTransactionRepository)


def test_service_builders_inject_concrete_repositories() -> None:
    db = MagicMock()

    spent_service = build_spent_service(db)
    assert isinstance(spent_service.repo, SpentRepository)
    assert isinstance(spent_service.category_repo, CategoryRepository)
    assert isinstance(spent_service.pm_repo, PaymentMethodRepository)
    assert spent_service.inv_service is not None

    income_service = build_income_service(db)
    assert isinstance(income_service.repo, IncomeRepository)
    assert isinstance(income_service.category_repo, IncomeCategoryRepository)
    assert isinstance(income_service.pm_repo, PaymentMethodRepository)
    assert isinstance(income_service.spent_repo, SpentRepository)

    balance_service = build_balance_service(db)
    assert isinstance(balance_service.limit_repo, SpendingLimitRepository)
    assert isinstance(balance_service.spent_repo, SpentRepository)
    assert isinstance(balance_service.category_repo, CategoryRepository)
    assert isinstance(balance_service.pm_repo, PaymentMethodRepository)

    assert isinstance(build_category_service(db).repo, CategoryRepository)
    assert isinstance(build_payment_method_service(db).repository, PaymentMethodRepository)

    account_service = build_account_service(db)
    assert isinstance(account_service.repository, AccountRepository)

    credit_card_service = build_credit_card_service(db)
    assert isinstance(credit_card_service.repository, CreditCardRepository)
    assert isinstance(credit_card_service.account_repository, AccountRepository)


class InMemoryCategoryRepository:
    """Structural fake that satisfies CategoryRepositoryProtocol without inheriting it."""

    def __init__(self, categories: list[Category]) -> None:
        self._store = {category.id: category for category in categories}

    async def get_by_id(self, category_id: UUID) -> Category | None:
        return self._store.get(category_id)

    async def get_by_key(self, key: str) -> Category | None:
        return next((c for c in self._store.values() if c.key == key), None)

    async def list(self, skip: int = 0, limit: int = 100) -> tuple[list[Category], int]:
        items = list(self._store.values())
        return items[skip : skip + limit], len(items)

    async def create(self, category_data: CategoryCreate) -> Category:
        category = Category(
            id=uuid4(),
            key=category_data.key,
            display_name=category_data.display_name,
            created_at=datetime(2026, 1, 1),
        )
        self._store[category.id] = category
        return category

    async def update(self, category_id: UUID, update_data: CategoryUpdate) -> Category | None:
        category = self._store.get(category_id)
        if category is None:
            return None
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(category, field, value)
        return category

    async def delete(self, category_id: UUID) -> bool:
        return self._store.pop(category_id, None) is not None


@pytest.mark.asyncio
async def test_category_service_accepts_structural_fake() -> None:
    category = Category(
        id=uuid4(),
        key="mercado",
        display_name="Mercado",
        created_at=datetime(2026, 1, 1),
    )
    service = CategoryService(InMemoryCategoryRepository([category]))

    items, total = await service.list()

    assert total == 1
    assert items[0].key == "mercado"
