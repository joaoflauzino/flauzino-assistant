"""Import facade: coordinates upload, listing, editing, bulk actions and commits."""

from uuid import UUID

from finance_api.core.decorators import handle_service_errors
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
from finance_api.services.imports.wiring import ImportCollaborators, ImportServiceDeps


class ImportService:
    """Thin coordinator that delegates each import use case to a collaborator."""

    def __init__(
        self,
        deps: ImportServiceDeps,
        collaborators: ImportCollaborators,
    ) -> None:
        self.batch_repo = deps.batch_repo
        self.tx_repo = deps.tx_repo
        self.rule_repo = deps.rule_repo
        self.classification_service = deps.classification_service
        self.account_repo = deps.account_repo
        self.credit_card_repo = deps.credit_card_repo
        self.spent_service = deps.spent_service
        self.income_service = deps.income_service
        self.category_repo = deps.category_repo
        self.income_category_repo = deps.income_category_repo
        self._collaborators = collaborators

    @handle_service_errors
    async def create_batch_from_upload(
        self,
        file_bytes: bytes,
        filename: str,
        account_id: UUID | None = None,
        credit_card_id: UUID | None = None,
    ) -> ImportBatchResponse:
        return await self._collaborators.upload.create_batch_from_upload(
            file_bytes=file_bytes,
            filename=filename,
            account_id=account_id,
            credit_card_id=credit_card_id,
        )

    @handle_service_errors
    async def list_batches(self) -> list[ImportBatchResponse]:
        batches = await self.batch_repo.list_all()
        return await self._collaborators.presenter.build_batch_list(list(batches))

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
        tx_responses = [await self._collaborators.presenter.to_tx_response(tx) for tx in items]
        return PaginatedResponse.create(tx_responses, total, page, size)

    @handle_service_errors
    async def update_transaction(
        self,
        tx_id: UUID,
        data: StagedTransactionUpdate,
    ) -> StagedTransactionResponse:
        return await self._collaborators.editor.update(tx_id, data)

    @handle_service_errors
    async def bulk_action(self, req: BulkActionRequest) -> BulkActionResult:
        return await self._collaborators.bulk.execute(req)

    @handle_service_errors
    async def link_transaction(self, tx_id: UUID) -> StagedTransactionResponse:
        return await self._collaborators.editor.link(tx_id)

    @handle_service_errors
    async def commit_approved(self, req: CommitRequest) -> CommitResult:
        return await self._collaborators.commit.commit(req)

    @handle_service_errors
    async def reclassify_batch(self, batch_id: UUID | None = None) -> ReclassifyResult:
        return await self._collaborators.reclassifier.reclassify(batch_id)

    @handle_service_errors
    async def get_summary(self) -> SummaryResponse:
        _, pending_count = await self.tx_repo.list_by_filter(status="PENDING", size=1)
        _, approved_count = await self.tx_repo.list_by_filter(status="APPROVED", size=1)
        return SummaryResponse(pending=pending_count, approved=approved_count)
