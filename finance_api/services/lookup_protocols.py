"""Structural contracts for lookup-by-key repository capabilities."""

from typing import Protocol

from finance_api.models.categories import Category
from finance_api.models.income_categories import IncomeCategory
from finance_api.models.payment_methods import PaymentMethod


class CategoryLookupProtocol(Protocol):
    """Structural contract for looking up expense categories by key."""

    async def get_by_key(self, key: str) -> Category | None: ...


class IncomeCategoryLookupProtocol(Protocol):
    """Structural contract for looking up income categories by key."""

    async def get_by_key(self, key: str) -> IncomeCategory | None: ...


class PaymentMethodLookupProtocol(Protocol):
    """Structural contract for looking up payment methods by key."""

    async def get_by_key(self, key: str) -> PaymentMethod | None: ...
