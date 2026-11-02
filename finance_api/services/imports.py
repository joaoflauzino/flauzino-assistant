"""Import facade: coordinates upload, listing, editing, bulk actions and commits."""

from uuid import UUID

from finance_api.core.decorators import handle_service_errors
from finance_api.importers.protocols import ImportTargetResolver
from finance_api.importers.registry import (
    StatementParserFactory,
    build_default_parser_factory,
    build_default_target_resolvers,
)
from finance_api.importers.schemas import StatementType
from finance_api.repositories.accounts import AccountRepositoryProtocol
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.category_rules import CategoryRuleRepositoryProtocol
from finance_api.repositories.credit_cards import CreditCardRepositoryProtocol
from finance_api.repositories.imports import ImportBatchRepositoryProtocol
from finance_api.repositories.income_categories import IncomeCategoryRepository
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.schemas.imports import (
    BulkActionRequest,
    BulkActionResult,
    CommitRequest,
    CommitResult,
    ImportBatchResponse,
    ReclassifyResult,
    StagedTransactionResponse,
    StagedTransactionUpdate,
    SummaryResponse,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.services.ai_classifier import AIClassifierClient
from finance_api.services.classification import ClassificationService
from finance_api.services.import_bulk import ImportBulkService
from finance_api.services.import_commit import CommitContextResolver, ImportCommitService
from finance_api.services.import_enrichment import BatchEnrichmentService
from finance_api.services.import_fingerprint import ImportFingerprintService
from finance_api.services.import_presenter import ImportBatchPresenter
from finance_api.services.import_reclassify import ImportReclassifyService
from finance_api.services.import_staging import StagingBuilder
from finance_api.services.import_strategies import (
    DuplicateDetectorStrategy,
    build_default_bulk_strategies,
    build_default_commit_strategies,
    build_default_duplicate_detectors,
)
from finance_api.services.import_transaction_editor import StagedTransactionEditor
from finance_api.services.import_upload import ImportUploadService
from finance_api.services.incomes import IncomeService
from finance_api.services.protocols import BulkActionStrategy, TransactionCommitStrategy
from finance_api.services.spents import SpentService


class ImportService:
    """Thin coordinator that delegates each import use case to a collaborator."""

    def __init__(
        self,
        batch_repo: ImportBatchRepositoryProtocol,
        tx_repo: StagedTransactionRepository,
        rule_repo: CategoryRuleRepositoryProtocol,
        classification_service: ClassificationService,
        account_repo: AccountRepositoryProtocol,
        credit_card_repo: CreditCardRepositoryProtocol,
        spent_service: SpentService,
        income_service: IncomeService,
        category_repo: CategoryRepository,
        income_category_repo: IncomeCategoryRepository,
        ai_client: AIClassifierClient | None = None,
        bulk_strategies: dict[str, BulkActionStrategy] | None = None,
        commit_strategies: dict[str, TransactionCommitStrategy] | None = None,
        parser_factory: StatementParserFactory | None = None,
        target_resolvers: dict[StatementType, ImportTargetResolver] | None = None,
        duplicate_detectors: dict[str, DuplicateDetectorStrategy] | None = None,
    ) -> None:
        self.batch_repo = batch_repo
        self.tx_repo = tx_repo
        self.rule_repo = rule_repo
        self.classification_service = classification_service
        self.account_repo = account_repo
        self.credit_card_repo = credit_card_repo
        self.spent_service = spent_service
        self.income_service = income_service
        self.category_repo = category_repo
        self.income_category_repo = income_category_repo
        self.ai_client = ai_client or AIClassifierClient()

        self._bulk_strategies = bulk_strategies or build_default_bulk_strategies(
            rule_repo=self.rule_repo,
            category_repo=self.category_repo,
            income_category_repo=self.income_category_repo,
        )
        self._commit_strategies = commit_strategies or build_default_commit_strategies(
            spent_service=self.spent_service,
            income_service=self.income_service,
        )
        self._parser_factory = parser_factory or build_default_parser_factory()
        self._target_resolvers = target_resolvers or build_default_target_resolvers(
            account_repo=self.account_repo,
            credit_card_repo=self.credit_card_repo,
        )
        self._duplicate_detectors = duplicate_detectors or build_default_duplicate_detectors()

        self._presenter = ImportBatchPresenter(
            batch_repo=self.batch_repo,
            account_repo=self.account_repo,
            credit_card_repo=self.credit_card_repo,
            spent_service=self.spent_service,
            income_service=self.income_service,
        )
        self._enrichment = BatchEnrichmentService(
            category_repo=self.category_repo,
            income_category_repo=self.income_category_repo,
            ai_client=self.ai_client,
        )
        self._upload = ImportUploadService(
            batch_repo=self.batch_repo,
            tx_repo=self.tx_repo,
            parser_factory=self._parser_factory,
            target_resolvers=self._target_resolvers,
            fingerprints=ImportFingerprintService(),
            staging_builder=StagingBuilder(
                tx_repo=self.tx_repo,
                classification_service=self.classification_service,
                duplicate_detectors=self._duplicate_detectors,
            ),
            enrichment_service=self._enrichment,
            presenter=self._presenter,
        )
        self._editor = StagedTransactionEditor(
            tx_repo=self.tx_repo,
            rule_repo=self.rule_repo,
            category_repo=self.category_repo,
            income_category_repo=self.income_category_repo,
            presenter=self._presenter,
        )
        self._bulk = ImportBulkService(
            tx_repo=self.tx_repo,
            bulk_strategies=self._bulk_strategies,
        )
        self._commit = ImportCommitService(
            tx_repo=self.tx_repo,
            context_resolver=CommitContextResolver(
                account_repo=self.account_repo,
                credit_card_repo=self.credit_card_repo,
            ),
            commit_strategies=self._commit_strategies,
        )
        self._reclassifier = ImportReclassifyService(
            tx_repo=self.tx_repo,
            rule_repo=self.rule_repo,
            enrichment_service=self._enrichment,
        )

    @handle_service_errors
    async def create_batch_from_upload(
        self,
        file_bytes: bytes,
        filename: str,
        account_id: UUID | None = None,
        credit_card_id: UUID | None = None,
    ) -> ImportBatchResponse:
        return await self._upload.create_batch_from_upload(
            file_bytes=file_bytes,
            filename=filename,
            account_id=account_id,
            credit_card_id=credit_card_id,
        )

    @handle_service_errors
    async def list_batches(self) -> list[ImportBatchResponse]:
        batches = await self.batch_repo.list_all()
        return await self._presenter.build_batch_list(list(batches))

    @handle_service_errors
    async def list_transactions(
        self,
        batch_id: UUID | None = None,
        status: str | None = None,
        kind: str | None = None,
        only_duplicates: bool = False,
        only_unclassified: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedResponse[StagedTransactionResponse]:
        items, total = await self.tx_repo.list_by_filter(
            batch_id=batch_id,
            status=status,
            kind=kind,
            only_duplicates=only_duplicates,
            only_unclassified=only_unclassified,
            page=page,
            size=size,
        )
        tx_responses = [await self._presenter.to_tx_response(tx) for tx in items]
        return PaginatedResponse.create(tx_responses, total, page, size)

    @handle_service_errors
    async def update_transaction(
        self,
        tx_id: UUID,
        data: StagedTransactionUpdate,
    ) -> StagedTransactionResponse:
        return await self._editor.update(tx_id, data)

    @handle_service_errors
    async def bulk_action(self, req: BulkActionRequest) -> BulkActionResult:
        return await self._bulk.execute(req)

    @handle_service_errors
    async def link_transaction(self, tx_id: UUID) -> StagedTransactionResponse:
        return await self._editor.link(tx_id)

    @handle_service_errors
    async def commit_approved(self, req: CommitRequest) -> CommitResult:
        return await self._commit.commit(req)

    @handle_service_errors
    async def reclassify_batch(self, batch_id: UUID | None = None) -> ReclassifyResult:
        return await self._reclassifier.reclassify(batch_id)

    @handle_service_errors
    async def get_summary(self) -> SummaryResponse:
        _, pending_count = await self.tx_repo.list_by_filter(status="PENDING", size=1)
        _, approved_count = await self.tx_repo.list_by_filter(status="APPROVED", size=1)
        return SummaryResponse(pending=pending_count, approved=approved_count)
