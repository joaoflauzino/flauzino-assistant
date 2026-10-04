from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from finance_api.core.dependencies import get_category_rule_repository, get_import_service
from finance_api.repositories.category_rules import CategoryRuleRepository
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
from finance_api.services.imports import ImportService

router = APIRouter()


@router.post("/", response_model=ImportBatchResponse, status_code=status.HTTP_201_CREATED)
async def upload_statement(
    file: UploadFile = File(..., description="Arquivo de extrato (CSV)"),
    account_id: Optional[UUID] = Form(None, description="ID da conta bancária"),
    credit_card_id: Optional[UUID] = Form(None, description="ID do cartão de crédito"),
    service: ImportService = Depends(get_import_service),
):
    """Realiza o upload de um arquivo de extrato bancário para staging."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    return await service.create_batch_from_upload(
        file_bytes=content,
        filename=file.filename or "extrato.csv",
        account_id=account_id,
        credit_card_id=credit_card_id,
    )


@router.get("/", response_model=list[ImportBatchResponse])
async def list_import_batches(
    service: ImportService = Depends(get_import_service),
):
    """Lista todos os lotes de importação registrados."""
    return await service.list_batches()


@router.get("/summary", response_model=SummaryResponse)
async def get_imports_summary(
    service: ImportService = Depends(get_import_service),
):
    """Retorna contadores de transações pendentes e aprovadas."""
    return await service.get_summary()


@router.get("/transactions", response_model=PaginatedResponse[StagedTransactionResponse])
async def list_staged_transactions(
    batch_id: Optional[UUID] = Query(None, description="Filtrar por ID do lote"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrar por status"),
    kind: Optional[str] = Query(None, description="Filtrar por tipo (EXPENSE, INCOME, etc.)"),
    only_duplicates: bool = Query(False, description="Filtrar apenas possíveis duplicatas"),
    only_unclassified: bool = Query(False, description="Filtrar apenas sem categoria"),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(50, ge=1, le=200, description="Tamanho da página"),
    service: ImportService = Depends(get_import_service),
):
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
    service: ImportService = Depends(get_import_service),
):
    """Atualiza categoria, tipo, descrição, localização ou status de uma transação pendente."""
    return await service.update_transaction(tx_id, data)


@router.post("/transactions/bulk", response_model=BulkActionResult)
async def bulk_action_transactions(
    req: BulkActionRequest,
    service: ImportService = Depends(get_import_service),
):
    """Executa ações em lote sobre transações selecionadas (approve, ignore, reopen, set_category)."""
    return await service.bulk_action(req)


@router.post("/transactions/{tx_id}/link", response_model=StagedTransactionResponse)
async def link_staged_transaction(
    tx_id: UUID,
    service: ImportService = Depends(get_import_service),
):
    """Vincula a transação pendente a um gasto/receita já existente identificado como duplicata."""
    return await service.link_transaction(tx_id)


@router.post("/commit", response_model=CommitResult)
async def commit_approved_transactions(
    req: CommitRequest = CommitRequest(),
    service: ImportService = Depends(get_import_service),
):
    """Efetiva todas as transações com status APPROVED, criando spents/incomes reais."""
    return await service.commit_approved(req)


@router.post("/{batch_id}/classify", response_model=ReclassifyResult)
async def reclassify_batch(
    batch_id: UUID,
    service: ImportService = Depends(get_import_service),
):
    """Executa reclassificação por IA para transações pendentes sem categoria em um lote."""
    return await service.reclassify_batch(batch_id)


# Regras de importação
rules_router = APIRouter()


@rules_router.get("/", response_model=list[ImportRuleResponse])
async def list_import_rules(
    rule_repo: CategoryRuleRepository = Depends(get_category_rule_repository),
):
    """Lista regras aprendidas e configuradas para classificação de comerciantes."""
    rules = await rule_repo.list_all()
    return [ImportRuleResponse.model_validate(r) for r in rules]


@rules_router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_import_rule(
    rule_id: UUID,
    rule_repo: CategoryRuleRepository = Depends(get_category_rule_repository),
):
    """Exclui uma regra de classificação."""
    deleted = await rule_repo.delete_by_id(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Regra não encontrada.")
