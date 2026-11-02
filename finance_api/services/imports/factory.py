"""Factory that assembles the ``ImportService`` façade and its collaborators."""

from finance_api.importers.registry import (
    build_default_parser_factory,
    build_default_target_resolvers,
)
from finance_api.services.ai_classifier import AIClassifierClient
from finance_api.services.imports.bulk import ImportBulkService
from finance_api.services.imports.bulk_strategies import build_default_bulk_strategies
from finance_api.services.imports.commit import CommitContextResolver, ImportCommitService
from finance_api.services.imports.commit_strategies import (
    build_default_commit_strategies,
    build_default_duplicate_detectors,
)
from finance_api.services.imports.enrichment import BatchEnrichmentService
from finance_api.services.imports.facade import ImportService
from finance_api.services.imports.fingerprint import ImportFingerprintService
from finance_api.services.imports.presenter import ImportBatchPresenter
from finance_api.services.imports.protocols import TransactionCommitStrategy
from finance_api.services.imports.reclassify import ImportReclassifyService
from finance_api.services.imports.staging import StagingBuilder
from finance_api.services.imports.transaction_editor import StagedTransactionEditor
from finance_api.services.imports.upload import ImportUploadService
from finance_api.services.imports.wiring import (
    ImportCollaborators,
    ImportOverrides,
    ImportServiceDeps,
)


def build_default_import_service(
    deps: ImportServiceDeps,
    overrides: ImportOverrides | None = None,
) -> ImportService:
    """Builds an ``ImportService`` wired with the default collaborator graph."""
    return ImportService(
        deps=deps,
        collaborators=build_default_collaborators(deps, overrides or ImportOverrides()),
    )


def build_default_collaborators(
    deps: ImportServiceDeps,
    overrides: ImportOverrides,
) -> ImportCollaborators:
    """Builds every use-case collaborator, honouring the injected overrides."""
    ai_client = overrides.ai_client or AIClassifierClient()
    presenter = ImportBatchPresenter(
        batch_repo=deps.batch_repo,
        account_repo=deps.account_repo,
        credit_card_repo=deps.credit_card_repo,
        spent_service=deps.spent_service,
        income_service=deps.income_service,
    )
    enrichment = BatchEnrichmentService(
        category_repo=deps.category_repo,
        income_category_repo=deps.income_category_repo,
        ai_client=ai_client,
    )
    return ImportCollaborators(
        presenter=presenter,
        upload=build_upload_collaborator(deps, presenter, enrichment, overrides),
        editor=build_editor_collaborator(deps, presenter),
        bulk=build_bulk_collaborator(deps, overrides),
        commit=build_commit_collaborator(deps, overrides.commit_strategies),
        reclassifier=ImportReclassifyService(
            tx_repo=deps.tx_repo,
            rule_repo=deps.rule_repo,
            enrichment_service=enrichment,
        ),
    )


def build_upload_collaborator(
    deps: ImportServiceDeps,
    presenter: ImportBatchPresenter,
    enrichment: BatchEnrichmentService,
    overrides: ImportOverrides,
) -> ImportUploadService:
    """Builds the upload pipeline, including parser and target resolution."""
    return ImportUploadService(
        batch_repo=deps.batch_repo,
        tx_repo=deps.tx_repo,
        parser_factory=overrides.parser_factory or build_default_parser_factory(),
        target_resolvers=overrides.target_resolvers
        or build_default_target_resolvers(
            account_repo=deps.account_repo,
            credit_card_repo=deps.credit_card_repo,
        ),
        fingerprints=ImportFingerprintService(),
        staging_builder=StagingBuilder(
            tx_repo=deps.tx_repo,
            classification_service=deps.classification_service,
            duplicate_detectors=overrides.duplicate_detectors
            or build_default_duplicate_detectors(),
        ),
        enrichment_service=enrichment,
        presenter=presenter,
    )


def build_editor_collaborator(
    deps: ImportServiceDeps,
    presenter: ImportBatchPresenter,
) -> StagedTransactionEditor:
    """Builds the single-transaction editor bound to the shared presenter."""
    return StagedTransactionEditor(
        tx_repo=deps.tx_repo,
        rule_repo=deps.rule_repo,
        category_repo=deps.category_repo,
        income_category_repo=deps.income_category_repo,
        presenter=presenter,
    )


def build_bulk_collaborator(
    deps: ImportServiceDeps,
    overrides: ImportOverrides,
) -> ImportBulkService:
    """Builds the bulk action service with kind-aware strategies."""
    return ImportBulkService(
        tx_repo=deps.tx_repo,
        bulk_strategies=overrides.bulk_strategies
        or build_default_bulk_strategies(
            rule_repo=deps.rule_repo,
            category_repo=deps.category_repo,
            income_category_repo=deps.income_category_repo,
        ),
    )


def build_commit_collaborator(
    deps: ImportServiceDeps,
    commit_strategies: dict[str, TransactionCommitStrategy] | None,
) -> ImportCommitService:
    """Builds the commit service resolved against accounts and credit cards."""
    return ImportCommitService(
        tx_repo=deps.tx_repo,
        context_resolver=CommitContextResolver(
            account_repo=deps.account_repo,
            credit_card_repo=deps.credit_card_repo,
        ),
        commit_strategies=commit_strategies
        or build_default_commit_strategies(
            spent_service=deps.spent_service,
            income_service=deps.income_service,
        ),
    )
