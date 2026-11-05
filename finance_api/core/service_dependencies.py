"""FastAPI providers for the finance_api services and import collaborators."""

from typing import Annotated

from fastapi import Depends

from finance_api.core.dependencies import (
    AccountRepoDep,
    CategoryRepoDep,
    CategoryRuleRepoDep,
    CreditCardRepoDep,
    ImportBatchRepoDep,
    IncomeCategoryRepoDep,
    IncomeRepoDep,
    InvoiceRepoDep,
    PaymentMethodRepoDep,
    PaymentResolutionServiceDep,
    SpendingLimitRepoDep,
    SpentRepoDep,
    StagedTransactionRepoDep,
)
from finance_api.importers.protocols import ImportTargetResolver
from finance_api.importers.registry import (
    StatementParserFactory,
    build_default_parser_factory,
    build_default_target_resolvers,
)
from finance_api.importers.schemas import StatementType
from finance_api.services.accounts import AccountService
from finance_api.services.balances import BalanceService
from finance_api.services.categories import CategoryService
from finance_api.services.classification.service import ClassificationService
from finance_api.services.credit_cards import CreditCardService
from finance_api.services.imports.facade import ImportService
from finance_api.services.imports.factory import build_default_import_service
from finance_api.services.imports.wiring import ImportOverrides, ImportServiceDeps
from finance_api.services.income_categories import IncomeCategoryService
from finance_api.services.incomes import IncomeService
from finance_api.services.invoices import InvoiceService
from finance_api.services.limits import SpendingLimitService
from finance_api.services.payment_methods import PaymentMethodService
from finance_api.services.spents import SpentService


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


def get_invoice_service(
    inv_repo: InvoiceRepoDep,
    pm_repo: PaymentMethodRepoDep,
) -> InvoiceService:
    return InvoiceService(inv_repo, pm_repo)


InvoiceServiceDep = Annotated[InvoiceService, Depends(get_invoice_service)]


def get_balance_service(
    limit_repo: SpendingLimitRepoDep,
    spent_repo: SpentRepoDep,
    category_repo: CategoryRepoDep,
    pm_repo: PaymentMethodRepoDep,
    inv_service: InvoiceServiceDep,
) -> BalanceService:
    """FastAPI dependency provider for BalanceService."""
    return BalanceService(
        limit_repo=limit_repo,
        spent_repo=spent_repo,
        category_repo=category_repo,
        pm_repo=pm_repo,
        inv_service=inv_service,
    )


BalanceServiceDep = Annotated[BalanceService, Depends(get_balance_service)]


def get_spending_limit_service(
    repo: SpendingLimitRepoDep,
    category_repo: CategoryRepoDep,
) -> SpendingLimitService:
    """FastAPI dependency provider for SpendingLimitService."""
    return SpendingLimitService(repo=repo, category_repo=category_repo)


SpendingLimitServiceDep = Annotated[SpendingLimitService, Depends(get_spending_limit_service)]


def get_spent_service(
    repo: SpentRepoDep,
    category_repo: CategoryRepoDep,
    pm_repo: PaymentMethodRepoDep,
    payment_resolver: PaymentResolutionServiceDep,
    inv_service: InvoiceServiceDep,
) -> SpentService:
    """FastAPI dependency provider for SpentService."""
    return SpentService(
        repo=repo,
        category_repo=category_repo,
        pm_repo=pm_repo,
        payment_resolver=payment_resolver,
        inv_service=inv_service,
    )


SpentServiceDep = Annotated[SpentService, Depends(get_spent_service)]


def get_category_service(repo: CategoryRepoDep) -> CategoryService:
    """FastAPI dependency provider for CategoryService."""
    return CategoryService(repo)


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


def get_payment_method_service(repo: PaymentMethodRepoDep) -> PaymentMethodService:
    """FastAPI dependency provider for PaymentMethodService."""
    return PaymentMethodService(repo)


PaymentMethodServiceDep = Annotated[PaymentMethodService, Depends(get_payment_method_service)]


def get_income_category_service(repo: IncomeCategoryRepoDep) -> IncomeCategoryService:
    """FastAPI dependency provider for IncomeCategoryService."""
    return IncomeCategoryService(repo)


IncomeCategoryServiceDep = Annotated[IncomeCategoryService, Depends(get_income_category_service)]


def get_income_service(
    repo: IncomeRepoDep,
    category_repo: IncomeCategoryRepoDep,
    pm_repo: PaymentMethodRepoDep,
    spent_repo: SpentRepoDep,
    payment_resolver: PaymentResolutionServiceDep,
) -> IncomeService:
    """FastAPI dependency provider for IncomeService."""
    return IncomeService(
        repo=repo,
        category_repo=category_repo,
        pm_repo=pm_repo,
        spent_repo=spent_repo,
        payment_resolver=payment_resolver,
    )


IncomeServiceDep = Annotated[IncomeService, Depends(get_income_service)]


def get_account_service(repo: AccountRepoDep) -> AccountService:
    """FastAPI dependency provider for AccountService."""
    return AccountService(repository=repo)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]


def get_credit_card_service(
    repo: CreditCardRepoDep,
    account_repo: AccountRepoDep,
) -> CreditCardService:
    """FastAPI dependency provider for CreditCardService."""
    return CreditCardService(repository=repo, account_repository=account_repo)


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
