from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.importers.protocols import ImportTargetResolver
from finance_api.importers.registry import (
    StatementParserFactory,
    build_default_parser_factory,
    build_default_target_resolvers,
)
from finance_api.importers.schemas import StatementType
from finance_api.repositories.accounts import AccountRepository, AccountRepositoryProtocol
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.category_rules import (
    CategoryRuleRepository,
    CategoryRuleRepositoryProtocol,
)
from finance_api.repositories.credit_cards import (
    CreditCardRepository,
    CreditCardRepositoryProtocol,
)
from finance_api.repositories.imports import (
    ImportBatchRepository,
    ImportBatchRepositoryProtocol,
)
from finance_api.repositories.income_categories import IncomeCategoryRepository
from finance_api.repositories.incomes import IncomeRepository
from finance_api.repositories.invoices import InvoiceRepository
from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.repositories.spents import SpentRepository
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.services.accounts import AccountService
from finance_api.services.balances import BalanceService
from finance_api.services.classification import ClassificationService
from finance_api.services.credit_cards import CreditCardService
from finance_api.services.import_factory import build_default_import_service
from finance_api.services.import_wiring import ImportOverrides, ImportServiceDeps
from finance_api.services.imports import ImportService
from finance_api.services.income_categories import IncomeCategoryService
from finance_api.services.incomes import IncomeService
from finance_api.services.invoices import InvoiceService
from finance_api.services.limits import SpendingLimitService
from finance_api.services.spents import SpentService

# 1. Database Session Lifecycle
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]


# 2. Repository Providers
def get_account_repository(db: DBSessionDep) -> AccountRepositoryProtocol:
    return AccountRepository(db)


AccountRepoDep = Annotated[AccountRepositoryProtocol, Depends(get_account_repository)]


def get_credit_card_repository(db: DBSessionDep) -> CreditCardRepositoryProtocol:
    return CreditCardRepository(db)


CreditCardRepoDep = Annotated[CreditCardRepositoryProtocol, Depends(get_credit_card_repository)]


def get_category_repository(db: DBSessionDep) -> CategoryRepository:
    return CategoryRepository(db)


CategoryRepoDep = Annotated[CategoryRepository, Depends(get_category_repository)]


def get_income_category_repository(db: DBSessionDep) -> IncomeCategoryRepository:
    return IncomeCategoryRepository(db)


IncomeCategoryRepoDep = Annotated[IncomeCategoryRepository, Depends(get_income_category_repository)]


def get_payment_method_repository(db: DBSessionDep) -> PaymentMethodRepository:
    return PaymentMethodRepository(db)


PaymentMethodRepoDep = Annotated[PaymentMethodRepository, Depends(get_payment_method_repository)]


def get_invoice_repository(db: DBSessionDep) -> InvoiceRepository:
    return InvoiceRepository(db)


InvoiceRepoDep = Annotated[InvoiceRepository, Depends(get_invoice_repository)]


def get_spent_repository(db: DBSessionDep) -> SpentRepository:
    return SpentRepository(db)


SpentRepoDep = Annotated[SpentRepository, Depends(get_spent_repository)]


def get_income_repository(db: DBSessionDep) -> IncomeRepository:
    return IncomeRepository(db)


IncomeRepoDep = Annotated[IncomeRepository, Depends(get_income_repository)]


def get_spending_limit_repository(db: DBSessionDep) -> SpendingLimitRepository:
    return SpendingLimitRepository(db)


SpendingLimitRepoDep = Annotated[SpendingLimitRepository, Depends(get_spending_limit_repository)]


def get_category_rule_repository(db: DBSessionDep) -> CategoryRuleRepositoryProtocol:
    return CategoryRuleRepository(db)


CategoryRuleRepoDep = Annotated[
    CategoryRuleRepositoryProtocol, Depends(get_category_rule_repository)
]


def get_import_batch_repository(db: DBSessionDep) -> ImportBatchRepositoryProtocol:
    return ImportBatchRepository(db)


ImportBatchRepoDep = Annotated[ImportBatchRepositoryProtocol, Depends(get_import_batch_repository)]


def get_staged_transaction_repository(db: DBSessionDep) -> StagedTransactionRepository:
    return StagedTransactionRepository(db)


StagedTransactionRepoDep = Annotated[
    StagedTransactionRepository, Depends(get_staged_transaction_repository)
]


# 3. Factory & Resolver Providers
def get_parser_factory() -> StatementParserFactory:
    return build_default_parser_factory()


ParserFactoryDep = Annotated[StatementParserFactory, Depends(get_parser_factory)]


def get_target_resolvers(
    acc_repo: AccountRepoDep,
    cc_repo: CreditCardRepoDep,
) -> dict[StatementType, ImportTargetResolver]:
    return build_default_target_resolvers(account_repo=acc_repo, credit_card_repo=cc_repo)


TargetResolversDep = Annotated[
    dict[StatementType, ImportTargetResolver], Depends(get_target_resolvers)
]


# 4. Service Providers
def get_invoice_service(
    inv_repo: InvoiceRepoDep,
    pm_repo: PaymentMethodRepoDep,
) -> InvoiceService:
    return InvoiceService(inv_repo, pm_repo)


InvoiceServiceDep = Annotated[InvoiceService, Depends(get_invoice_service)]


def get_balance_service(db: DBSessionDep) -> BalanceService:
    """FastAPI dependency provider for BalanceService."""
    pm_repo = PaymentMethodRepository(db)
    inv_repo = InvoiceRepository(db)
    return BalanceService(
        limit_repo=SpendingLimitRepository(db),
        spent_repo=SpentRepository(db),
        category_repo=CategoryRepository(db),
        pm_repo=pm_repo,
        inv_service=InvoiceService(inv_repo, pm_repo),
    )


BalanceServiceDep = Annotated[BalanceService, Depends(get_balance_service)]


def get_spending_limit_service(db: DBSessionDep) -> SpendingLimitService:
    """FastAPI dependency provider for SpendingLimitService."""
    return SpendingLimitService(
        repo=SpendingLimitRepository(db),
        category_repo=CategoryRepository(db),
    )


SpendingLimitServiceDep = Annotated[SpendingLimitService, Depends(get_spending_limit_service)]


def get_spent_service(db: DBSessionDep) -> SpentService:
    """FastAPI dependency provider for SpentService."""
    pm_repo = PaymentMethodRepository(db)
    inv_repo = InvoiceRepository(db)
    return SpentService(
        repo=SpentRepository(db),
        category_repo=CategoryRepository(db),
        pm_repo=pm_repo,
        inv_service=InvoiceService(inv_repo, pm_repo),
    )


SpentServiceDep = Annotated[SpentService, Depends(get_spent_service)]


def get_income_category_service(db: DBSessionDep) -> IncomeCategoryService:
    """FastAPI dependency provider for IncomeCategoryService."""
    return IncomeCategoryService(repo=IncomeCategoryRepository(db))


IncomeCategoryServiceDep = Annotated[IncomeCategoryService, Depends(get_income_category_service)]


def get_income_service(db: DBSessionDep) -> IncomeService:
    """FastAPI dependency provider for IncomeService."""
    return IncomeService(
        repo=IncomeRepository(db),
        category_repo=IncomeCategoryRepository(db),
        pm_repo=PaymentMethodRepository(db),
        spent_repo=SpentRepository(db),
    )


IncomeServiceDep = Annotated[IncomeService, Depends(get_income_service)]


def get_account_service(db: DBSessionDep) -> AccountService:
    """FastAPI dependency provider for AccountService."""
    return AccountService(repository=AccountRepository(db))


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]


def get_credit_card_service(db: DBSessionDep) -> CreditCardService:
    """FastAPI dependency provider for CreditCardService."""
    return CreditCardService(
        repository=CreditCardRepository(db),
        account_repository=AccountRepository(db),
    )


CreditCardServiceDep = Annotated[CreditCardService, Depends(get_credit_card_service)]


def get_classification_service(rule_repo: CategoryRuleRepoDep) -> ClassificationService:
    """FastAPI dependency provider for ClassificationService."""
    return ClassificationService(rule_repo=rule_repo)


ClassificationServiceDep = Annotated[ClassificationService, Depends(get_classification_service)]


def get_import_service(
    batch_repo: ImportBatchRepoDep,
    tx_repo: StagedTransactionRepoDep,
    rule_repo: CategoryRuleRepoDep,
    clf_service: ClassificationServiceDep,
    acc_repo: AccountRepoDep,
    cc_repo: CreditCardRepoDep,
    cat_repo: CategoryRepoDep,
    inc_cat_repo: IncomeCategoryRepoDep,
    spent_svc: SpentServiceDep,
    inc_svc: IncomeServiceDep,
    parser_factory: ParserFactoryDep,
    target_resolvers: TargetResolversDep,
) -> ImportService:
    deps = ImportServiceDeps(
        batch_repo=batch_repo,
        tx_repo=tx_repo,
        rule_repo=rule_repo,
        classification_service=clf_service,
        account_repo=acc_repo,
        credit_card_repo=cc_repo,
        spent_service=spent_svc,
        income_service=inc_svc,
        category_repo=cat_repo,
        income_category_repo=inc_cat_repo,
    )
    overrides = ImportOverrides(
        parser_factory=parser_factory,
        target_resolvers=target_resolvers,
    )
    return build_default_import_service(deps, overrides)


ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]
