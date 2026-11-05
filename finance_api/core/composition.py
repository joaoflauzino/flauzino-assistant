"""Programmatic composition of services for CLI, MCP and background jobs.

The FastAPI dependency graph is declared in ``core.service_dependencies``; these
builders reuse the same providers for callers that only have a database session.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.dependencies import (
    get_account_repository,
    get_category_repository,
    get_credit_card_repository,
    get_income_category_repository,
    get_income_repository,
    get_invoice_repository,
    get_payment_method_repository,
    get_spending_limit_repository,
    get_spent_repository,
)
from finance_api.core.service_dependencies import (
    get_account_service,
    get_balance_service,
    get_category_service,
    get_credit_card_service,
    get_income_category_service,
    get_income_service,
    get_invoice_service,
    get_payment_method_service,
    get_spent_service,
)
from finance_api.services.accounts import AccountService
from finance_api.services.balances import BalanceService
from finance_api.services.categories import CategoryService
from finance_api.services.credit_cards import CreditCardService
from finance_api.services.income_categories import IncomeCategoryService
from finance_api.services.incomes import IncomeService
from finance_api.services.invoices import InvoiceService
from finance_api.services.payment_methods import PaymentMethodService
from finance_api.services.payment_resolution import PaymentResolutionService
from finance_api.services.spents import SpentService


def build_payment_resolution_service(db: AsyncSession) -> PaymentResolutionService:
    """Composes the payment resolver outside the FastAPI dependency graph."""
    return PaymentResolutionService(
        card_repo=get_credit_card_repository(db),
        account_repo=get_account_repository(db),
    )


def build_invoice_service(db: AsyncSession) -> InvoiceService:
    """Composes the invoice service outside the FastAPI dependency graph."""
    return get_invoice_service(
        inv_repo=get_invoice_repository(db),
        pm_repo=get_payment_method_repository(db),
    )


def build_balance_service(db: AsyncSession) -> BalanceService:
    """Composes the balance service outside the FastAPI dependency graph."""
    return get_balance_service(
        limit_repo=get_spending_limit_repository(db),
        spent_repo=get_spent_repository(db),
        category_repo=get_category_repository(db),
        pm_repo=get_payment_method_repository(db),
        inv_service=build_invoice_service(db),
    )


def build_spent_service(db: AsyncSession) -> SpentService:
    """Composes the spent service outside the FastAPI dependency graph."""
    return get_spent_service(
        repo=get_spent_repository(db),
        category_repo=get_category_repository(db),
        pm_repo=get_payment_method_repository(db),
        payment_resolver=build_payment_resolution_service(db),
        inv_service=build_invoice_service(db),
    )


def build_income_service(db: AsyncSession) -> IncomeService:
    """Composes the income service outside the FastAPI dependency graph."""
    return get_income_service(
        repo=get_income_repository(db),
        category_repo=get_income_category_repository(db),
        pm_repo=get_payment_method_repository(db),
        spent_repo=get_spent_repository(db),
        payment_resolver=build_payment_resolution_service(db),
    )


def build_category_service(db: AsyncSession) -> CategoryService:
    """Composes the category service outside the FastAPI dependency graph."""
    return get_category_service(repo=get_category_repository(db))


def build_payment_method_service(db: AsyncSession) -> PaymentMethodService:
    """Composes the payment-method service outside the FastAPI dependency graph."""
    return get_payment_method_service(repo=get_payment_method_repository(db))


def build_income_category_service(db: AsyncSession) -> IncomeCategoryService:
    """Composes the income-category service outside the FastAPI dependency graph."""
    return get_income_category_service(repo=get_income_category_repository(db))


def build_account_service(db: AsyncSession) -> AccountService:
    """Composes the account service outside the FastAPI dependency graph."""
    return get_account_service(repo=get_account_repository(db))


def build_credit_card_service(db: AsyncSession) -> CreditCardService:
    """Composes the credit-card service outside the FastAPI dependency graph."""
    return get_credit_card_service(
        repo=get_credit_card_repository(db),
        account_repo=get_account_repository(db),
    )
