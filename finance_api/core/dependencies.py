"""FastAPI providers for the database session and repository contracts."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
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
from finance_api.repositories.protocols import (
    AccountRepositoryProtocol,
    CategoryRepositoryProtocol,
    CategoryRuleRepositoryProtocol,
    CreditCardRepositoryProtocol,
    ImportBatchRepositoryProtocol,
    IncomeCategoryRepositoryProtocol,
    IncomeRepositoryProtocol,
    InvoiceRepositoryProtocol,
    PaymentMethodRepositoryProtocol,
    SpendingLimitRepositoryProtocol,
    SpentRepositoryProtocol,
    StagedTransactionRepositoryProtocol,
)
from finance_api.repositories.spents import SpentRepository
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.services.payment_resolution import PaymentResolutionService

DBSessionDep = Annotated[AsyncSession, Depends(get_db)]


def get_account_repository(db: DBSessionDep) -> AccountRepositoryProtocol:
    return AccountRepository(db)


AccountRepoDep = Annotated[AccountRepositoryProtocol, Depends(get_account_repository)]


def get_credit_card_repository(db: DBSessionDep) -> CreditCardRepositoryProtocol:
    return CreditCardRepository(db)


CreditCardRepoDep = Annotated[CreditCardRepositoryProtocol, Depends(get_credit_card_repository)]


def get_category_repository(db: DBSessionDep) -> CategoryRepositoryProtocol:
    return CategoryRepository(db)


CategoryRepoDep = Annotated[CategoryRepositoryProtocol, Depends(get_category_repository)]


def get_income_category_repository(db: DBSessionDep) -> IncomeCategoryRepositoryProtocol:
    return IncomeCategoryRepository(db)


IncomeCategoryRepoDep = Annotated[
    IncomeCategoryRepositoryProtocol, Depends(get_income_category_repository)
]


def get_payment_method_repository(db: DBSessionDep) -> PaymentMethodRepositoryProtocol:
    return PaymentMethodRepository(db)


PaymentMethodRepoDep = Annotated[
    PaymentMethodRepositoryProtocol, Depends(get_payment_method_repository)
]


def get_invoice_repository(db: DBSessionDep) -> InvoiceRepositoryProtocol:
    return InvoiceRepository(db)


InvoiceRepoDep = Annotated[InvoiceRepositoryProtocol, Depends(get_invoice_repository)]


def get_spent_repository(db: DBSessionDep) -> SpentRepositoryProtocol:
    return SpentRepository(db)


SpentRepoDep = Annotated[SpentRepositoryProtocol, Depends(get_spent_repository)]


def get_income_repository(db: DBSessionDep) -> IncomeRepositoryProtocol:
    return IncomeRepository(db)


IncomeRepoDep = Annotated[IncomeRepositoryProtocol, Depends(get_income_repository)]


def get_spending_limit_repository(db: DBSessionDep) -> SpendingLimitRepositoryProtocol:
    return SpendingLimitRepository(db)


SpendingLimitRepoDep = Annotated[
    SpendingLimitRepositoryProtocol, Depends(get_spending_limit_repository)
]


def get_category_rule_repository(db: DBSessionDep) -> CategoryRuleRepositoryProtocol:
    return CategoryRuleRepository(db)


CategoryRuleRepoDep = Annotated[
    CategoryRuleRepositoryProtocol, Depends(get_category_rule_repository)
]


def get_import_batch_repository(db: DBSessionDep) -> ImportBatchRepositoryProtocol:
    return ImportBatchRepository(db)


ImportBatchRepoDep = Annotated[ImportBatchRepositoryProtocol, Depends(get_import_batch_repository)]


def get_staged_transaction_repository(db: DBSessionDep) -> StagedTransactionRepositoryProtocol:
    return StagedTransactionRepository(db)


StagedTransactionRepoDep = Annotated[
    StagedTransactionRepositoryProtocol, Depends(get_staged_transaction_repository)
]


def get_payment_resolution_service(
    card_repo: CreditCardRepoDep,
    account_repo: AccountRepoDep,
) -> PaymentResolutionService:
    return PaymentResolutionService(card_repo=card_repo, account_repo=account_repo)


PaymentResolutionServiceDep = Annotated[
    PaymentResolutionService, Depends(get_payment_resolution_service)
]
