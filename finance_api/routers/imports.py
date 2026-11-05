from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from finance_api.core.exceptions import ValidationError
from finance_api.core.service_dependencies import ClassificationServiceDep, ImportServiceDep
from finance_api.models.category_rules import CategoryRule
from finance_api.schemas.imports import (
    BulkActionRequest,
    BulkActionResult,
    CommitRequest,
    CommitResult,
    ImportBatchResponse,
    ImportRuleResponse,
    ReclassifyResult,
    StagedTransactionResponse,
    StagedTransactionUpdate,
    SummaryResponse,
)
from finance_api.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.post("/", response_model=ImportBatchResponse, status_code=status.HTTP_201_CREATED)
async def upload_statement(
    service: ImportServiceDep,
    file: UploadFile = File(..., description="Arquivo de extrato (CSV)"),
    account_id: UUID | None = Form(None, description="ID da conta bancária"),
    credit_card_id: UUID | None = Form(None, description="ID do cartão de crédito"),
) -> ImportBatchResponse:
    """Realiza o upload de um arquivo de extrato bancário para staging."""
    content = await file.read()
    if not content:
        raise ValidationError("Arquivo vazio.")
    return await service.create_batch_from_upload(
        file_bytes=content,
        filename=file.filename or "extrato.csv",
        account_id=account_id,
        credit_card_id=credit_card_id,
    )


@router.get("/", response_model=list[ImportBatchResponse])
async def list_import_batches(
    service: ImportServiceDep,
) -> list[ImportBatchResponse]:
    """Lista todos os lotes de importação registrados."""
    return await service.list_batches()


@router.get("/summary", response_model=SummaryResponse)
async def get_imports_summary(
    service: ImportServiceDep,
) -> SummaryResponse:
    """Retorna contadores de transações pendentes e aprovadas."""
    return await service.get_summary()


@router.get("/transactions", response_model=PaginatedResponse[StagedTransactionResponse])
async def list_staged_transactions(
    service: ImportServiceDep,
    batch_id: UUID | None = Query(None, description="Filtrar por ID do lote"),
    status_filter: str | None = Query(None, alias="status", description="Filtrar por status"),
    kind: str | None = Query(None, description="Filtrar por tipo (EXPENSE, INCOME, etc.)"),
    only_duplicates: bool = Query(False, description="Filtrar apenas possíveis duplicatas"),
    only_unclassified: bool = Query(False, description="Filtrar apenas sem categoria"),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(50, ge=1, le=200, description="Tamanho da página"),
) -> PaginatedResponse[StagedTransactionResponse]:
    """Lista transações em staging com paginação e filtros."""
    return await service.list_transactions(
        batch_id=batch_id,
        status=status_filter,
        kind=kind,
        only_duplicates=only_duplicates,
        only_unclassified=only_unclassified,
        page=page,
        size=size,
    )


@router.patch("/transactions/{tx_id}", response_model=StagedTransactionResponse)
async def update_staged_transaction(
    tx_id: UUID,
    data: StagedTransactionUpdate,
    service: ImportServiceDep,
) -> StagedTransactionResponse:
    """Atualiza categoria, tipo, descrição, localização ou status de uma transação pendente."""
    return await service.update_transaction(tx_id, data)


@router.post("/transactions/bulk", response_model=BulkActionResult)
async def bulk_action_transactions(
    req: BulkActionRequest,
    service: ImportServiceDep,
) -> BulkActionResult:
    """Executa ações em lote sobre transações selecionadas (approve, ignore, reopen, set_category)."""
    return await service.bulk_action(req)


@router.post("/transactions/{tx_id}/link", response_model=StagedTransactionResponse)
async def link_staged_transaction(
    tx_id: UUID,
    service: ImportServiceDep,
) -> StagedTransactionResponse:
    """Vincula a transação pendente a um gasto/receita já existente identificado como duplicata."""
    return await service.link_transaction(tx_id)


@router.post("/commit", response_model=CommitResult)
async def commit_approved_transactions(
    service: ImportServiceDep,
    req: CommitRequest = CommitRequest(),
) -> CommitResult:
    """Efetiva todas as transações com status APPROVED, criando spents/incomes reais."""
    return await service.commit_approved(req)


@router.post("/{batch_id}/classify", response_model=ReclassifyResult)
async def reclassify_batch(
    batch_id: UUID,
    service: ImportServiceDep,
) -> ReclassifyResult:
    """Executa reclassificação por IA para transações pendentes sem categoria em um lote."""
    return await service.reclassify_batch(batch_id)


# Regras de importação
rules_router = APIRouter()


@rules_router.get("/", response_model=list[ImportRuleResponse])
async def list_import_rules(
    service: ClassificationServiceDep,
) -> Sequence[CategoryRule]:
    """Lista regras aprendidas e configuradas para classificação de comerciantes."""
    return await service.list_rules()


@rules_router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_import_rule(
    rule_id: UUID,
    service: ClassificationServiceDep,
) -> None:
    """Exclui uma regra de classificação."""
    await service.delete_rule(rule_id)
