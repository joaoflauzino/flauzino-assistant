from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from finance_api.core.exceptions import EntityConflictError, ValidationError
from finance_api.importers.schemas import (
    ParsedStatement,
    ParsedTransaction,
    ResolvedImportTarget,
    StatementMetadata,
    StatementType,
)
from finance_api.models.import_batches import ImportBatch
from finance_api.services.import_upload import ImportUploadService

SP_TZ = ZoneInfo("America/Sao_Paulo")


def _transaction() -> ParsedTransaction:
    return ParsedTransaction(
        occurred_at=datetime(2026, 10, 1, 9, 0, tzinfo=SP_TZ),
        posted_at=None,
        raw_title="SUPERMERCADO",
        raw_description=None,
        raw_row={},
        amount=Decimal("100.00"),
        direction="OUT",
    )


def _parsed() -> ParsedStatement:
    return ParsedStatement(
        metadata=StatementMetadata(
            parser_name="c6_checking_csv",
            bank_name="C6",
            statement_type=StatementType.ACCOUNT,
            period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 30),
        ),
        transactions=[_transaction()],
    )


def _service(*, parse: ParsedStatement, target: ResolvedImportTarget):
    parser = MagicMock(name="parser", statement_type=StatementType.ACCOUNT)
    parser.parse = MagicMock(return_value=parse)
    parser_factory = MagicMock()
    parser_factory.detect_and_create = MagicMock(return_value=parser)

    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=target)

    batch = ImportBatch(
        id=uuid4(),
        parser="c6_checking_csv",
        filename="extrato.csv",
        file_sha256="digest",
        total_rows=len(parse.transactions),
        new_rows=len(parse.transactions),
        duplicate_rows=0,
        possible_duplicates=0,
        ai_used=False,
        created_at=datetime(2026, 10, 3, 13, 0, tzinfo=SP_TZ),
    )
    batch_repo = MagicMock()
    batch_repo.get_by_sha256 = AsyncMock(return_value=None)
    batch_repo.create = AsyncMock(return_value=batch)
    batch_repo.update_batch_stats = AsyncMock(return_value=batch)
    batch_repo.get_counts_by_status = AsyncMock(return_value={"pending": 1})

    tx_repo = MagicMock()
    tx_repo.get_existing_fingerprints = AsyncMock(return_value=set())
    tx_repo.create_many = AsyncMock()

    fingerprints = MagicMock()
    fingerprints.sha256 = MagicMock(return_value="digest")
    fingerprints.build_map = MagicMock(
        return_value=[(tx, f"fp-{index}") for index, tx in enumerate(parse.transactions)],
    )

    staging_builder = MagicMock()
    staging_builder.build = AsyncMock(return_value=([], 0))
    enrichment_service = MagicMock()
    enrichment_service.enrich_staged = AsyncMock(return_value=False)
    presenter = MagicMock()
    presenter.build_batch_response = MagicMock(return_value="response")

    service = ImportUploadService(
        batch_repo=batch_repo,
        tx_repo=tx_repo,
        parser_factory=parser_factory,
        target_resolvers={StatementType.ACCOUNT: resolver},
        fingerprints=fingerprints,
        staging_builder=staging_builder,
        enrichment_service=enrichment_service,
        presenter=presenter,
    )
    return service, parser_factory, batch_repo, tx_repo, staging_builder, enrichment_service


def _target() -> ResolvedImportTarget:
    return ResolvedImportTarget(
        account_id=uuid4(),
        credit_card_id=None,
        target_key="c6_joao",
        target_name="C6",
    )


@pytest.mark.asyncio
async def test_upload_without_new_rows_skips_staging() -> None:
    service, parser_factory, batch_repo, tx_repo, staging_builder, _ = _service(
        parse=_parsed(),
        target=_target(),
    )
    tx_repo.get_existing_fingerprints = AsyncMock(return_value={"fp-0"})

    response = await service.create_batch_from_upload(b"content", "extrato.csv")

    assert response == "response"
    parser_factory.detect_and_create.assert_called_once_with(b"content", "extrato.csv")
    batch_repo.create.assert_awaited_once()
    staging_builder.build.assert_not_awaited()
    tx_repo.create_many.assert_not_awaited()
    batch_repo.update_batch_stats.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_with_new_rows_stages_enriches_and_updates_stats() -> None:
    service, _, batch_repo, tx_repo, staging_builder, enrichment_service = _service(
        parse=_parsed(),
        target=_target(),
    )
    staged = [MagicMock()]
    staging_builder.build = AsyncMock(return_value=(staged, 2))
    enrichment_service.enrich_staged = AsyncMock(return_value=True)

    response = await service.create_batch_from_upload(b"content", "extrato.csv")

    assert response == "response"
    staging_builder.build.assert_awaited_once()
    enrichment_service.enrich_staged.assert_awaited_once_with(staged)
    tx_repo.create_many.assert_awaited_once_with(staged)
    batch_repo.update_batch_stats.assert_awaited_once()
    assert batch_repo.update_batch_stats.call_args.kwargs == {
        "batch": batch_repo.create.return_value,
        "possible_duplicates": 2,
        "ai_used": True,
    }


@pytest.mark.asyncio
async def test_upload_rejects_already_imported_file() -> None:
    service, _, batch_repo, _, _, _ = _service(parse=_parsed(), target=_target())
    batch_repo.get_by_sha256 = AsyncMock(
        return_value=ImportBatch(
            id=uuid4(),
            created_at=datetime(2026, 10, 1, 10, 0, tzinfo=SP_TZ),
        ),
    )

    with pytest.raises(EntityConflictError):
        await service.create_batch_from_upload(b"content", "extrato.csv")


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_statement_type() -> None:
    service, _, _, _, _, _ = _service(parse=_parsed(), target=_target())
    service._target_resolvers = {}

    with pytest.raises(ValidationError):
        await service.create_batch_from_upload(b"content", "extrato.csv")
