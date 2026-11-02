"""Upload pipeline: parse, deduplicate, stage and enrich a bank statement file."""

from uuid import UUID

from finance_api.core.exceptions import EntityConflictError, ValidationError
from finance_api.importers.protocols import ImportTargetResolver
from finance_api.importers.registry import StatementParserFactory
from finance_api.importers.schemas import (
    ParsedStatement,
    ParsedTransaction,
    ResolvedImportTarget,
    StatementType,
)
from finance_api.models.import_batches import ImportBatch
from finance_api.repositories.imports import ImportBatchRepositoryProtocol
from finance_api.repositories.staged_transactions import StagedTransactionRepository
from finance_api.schemas.imports import ImportBatchResponse
from finance_api.services.imports.enrichment import BatchEnrichmentService
from finance_api.services.imports.fingerprint import ImportFingerprintService
from finance_api.services.imports.presenter import ImportBatchPresenter
from finance_api.services.imports.staging import StagingBuilder

BANK_HINT = "c6"


class ImportUploadService:
    """Orchestrates the statement upload pipeline into a staged import batch."""

    def __init__(
        self,
        batch_repo: ImportBatchRepositoryProtocol,
        tx_repo: StagedTransactionRepository,
        parser_factory: StatementParserFactory,
        target_resolvers: dict[StatementType, ImportTargetResolver],
        fingerprints: ImportFingerprintService,
        staging_builder: StagingBuilder,
        enrichment_service: BatchEnrichmentService,
        presenter: ImportBatchPresenter,
    ) -> None:
        self._batch_repo = batch_repo
        self._tx_repo = tx_repo
        self._parser_factory = parser_factory
        self._target_resolvers = target_resolvers
        self._fingerprints = fingerprints
        self._staging_builder = staging_builder
        self._enrichment_service = enrichment_service
        self._presenter = presenter

    async def create_batch_from_upload(
        self,
        file_bytes: bytes,
        filename: str,
        account_id: UUID | None = None,
        credit_card_id: UUID | None = None,
    ) -> ImportBatchResponse:
        """Parses the uploaded file and persists a batch with its staged rows."""
        parser = self._parser_factory.detect_and_create(file_bytes, filename)
        target = await self._resolve_target(parser.statement_type, account_id, credit_card_id)
        file_sha256 = self._fingerprints.sha256(file_bytes)
        await self._ensure_not_imported(file_sha256, filename)

        parsed = parser.parse(file_bytes, filename)
        new_pairs = await self._select_new_pairs(parsed.transactions, target)
        batch = await self._create_batch(parsed, target, file_sha256, filename, len(new_pairs))

        if new_pairs:
            batch = await self._stage_rows(batch, target, parser.statement_type, new_pairs)
        return await self._build_response(batch, target)

    async def _resolve_target(
        self,
        statement_type: StatementType,
        account_id: UUID | None,
        credit_card_id: UUID | None,
    ) -> ResolvedImportTarget:
        resolver = self._target_resolvers.get(statement_type)
        if resolver is None:
            raise ValidationError(
                f"Tipo de extrato '{statement_type}' não suportado para importação."
            )
        return await resolver.resolve(account_id, credit_card_id, bank_hint=BANK_HINT)

    async def _ensure_not_imported(self, file_sha256: str, filename: str) -> None:
        existing_batch = await self._batch_repo.get_by_sha256(file_sha256)
        if not existing_batch:
            return
        imported_at = existing_batch.created_at.strftime("%d/%m/%Y %H:%M")
        raise EntityConflictError(
            f"Este arquivo ('{filename}') já foi importado anteriormente em {imported_at}."
        )

    async def _select_new_pairs(
        self,
        transactions: list[ParsedTransaction],
        target: ResolvedImportTarget,
    ) -> list[tuple[ParsedTransaction, str]]:
        fingerprint_map = self._fingerprints.build_map(target.target_key, transactions)
        existing = await self._tx_repo.get_existing_fingerprints(
            [fingerprint for _, fingerprint in fingerprint_map]
        )
        return [
            (tx, fingerprint) for tx, fingerprint in fingerprint_map if fingerprint not in existing
        ]

    async def _create_batch(
        self,
        parsed: ParsedStatement,
        target: ResolvedImportTarget,
        file_sha256: str,
        filename: str,
        new_rows: int,
    ) -> ImportBatch:
        batch = ImportBatch(
            account_id=target.account_id,
            credit_card_id=target.credit_card_id,
            parser=parsed.metadata.parser_name,
            filename=filename,
            file_sha256=file_sha256,
            period_start=parsed.metadata.period_start,
            period_end=parsed.metadata.period_end,
            total_rows=len(parsed.transactions),
            new_rows=new_rows,
            duplicate_rows=len(parsed.transactions) - new_rows,
            possible_duplicates=0,
            ai_used=False,
        )
        return await self._batch_repo.create(batch)

    async def _stage_rows(
        self,
        batch: ImportBatch,
        target: ResolvedImportTarget,
        statement_type: StatementType,
        new_pairs: list[tuple[ParsedTransaction, str]],
    ) -> ImportBatch:
        staged_list, possible_duplicates = await self._staging_builder.build(
            batch_id=batch.id,
            target=target,
            new_pairs=new_pairs,
            is_credit_card=statement_type == StatementType.CREDIT_CARD,
        )
        ai_used = await self._enrichment_service.enrich_staged(staged_list)
        await self._tx_repo.create_many(staged_list)
        return await self._batch_repo.update_batch_stats(
            batch=batch,
            possible_duplicates=possible_duplicates,
            ai_used=ai_used,
        )

    async def _build_response(
        self,
        batch: ImportBatch,
        target: ResolvedImportTarget,
    ) -> ImportBatchResponse:
        counts = await self._batch_repo.get_counts_by_status(batch.id)
        return self._presenter.build_batch_response(batch, target, counts)
