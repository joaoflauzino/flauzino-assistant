"""Wiring contracts for the import façade: core dependencies, overrides and collaborators."""

from dataclasses import dataclass

from finance_api.importers.protocols import ImportTargetResolver
from finance_api.importers.registry import StatementParserFactory
from finance_api.importers.schemas import StatementType
from finance_api.repositories.accounts import AccountRepositoryProtocol
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.category_rules import CategoryRuleRepositoryProtocol
from finance_api.repositories.credit_cards import CreditCardRepositoryProtocol
from finance_api.repositories.imports import ImportBatchRepositoryProtocol
from finance_api.repositories.income_categories import IncomeCategoryRepository
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.services.classification.ai_classifier import AIClassifierClient
from finance_api.services.classification.service import ClassificationService
from finance_api.services.imports.bulk import ImportBulkService
from finance_api.services.imports.commit import ImportCommitService
from finance_api.services.imports.presenter import ImportBatchPresenter
from finance_api.services.imports.protocols import (
    BulkActionStrategy,
    DuplicateDetectorStrategy,
    TransactionCommitStrategy,
)
from finance_api.services.imports.reclassify import ImportReclassifyService
from finance_api.services.imports.transaction_editor import StagedTransactionEditor
from finance_api.services.imports.upload import ImportUploadService
from finance_api.services.incomes import IncomeService
from finance_api.services.spents import SpentService


@dataclass(frozen=True, slots=True)
class ImportServiceDeps:
    """Repositories and services every import use case needs."""

    batch_repo: ImportBatchRepositoryProtocol
    tx_repo: StagedTransactionRepository
    rule_repo: CategoryRuleRepositoryProtocol
    classification_service: ClassificationService
    account_repo: AccountRepositoryProtocol
    credit_card_repo: CreditCardRepositoryProtocol
    spent_service: SpentService
    income_service: IncomeService
    category_repo: CategoryRepository
    income_category_repo: IncomeCategoryRepository


@dataclass(frozen=True, slots=True)
class ImportOverrides:
    """Optional collaborator overrides, used by tests and alternative deployments."""

    ai_client: AIClassifierClient | None = None
    bulk_strategies: dict[str, BulkActionStrategy] | None = None
    commit_strategies: dict[str, TransactionCommitStrategy] | None = None
    parser_factory: StatementParserFactory | None = None
    target_resolvers: dict[StatementType, ImportTargetResolver] | None = None
    duplicate_detectors: dict[str, DuplicateDetectorStrategy] | None = None


@dataclass(frozen=True, slots=True)
class ImportCollaborators:
    """One collaborator per public import use case, behind the façade."""

    presenter: ImportBatchPresenter
    upload: ImportUploadService
    editor: StagedTransactionEditor
    bulk: ImportBulkService
    commit: ImportCommitService
    reclassifier: ImportReclassifyService
