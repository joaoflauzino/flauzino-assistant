from uuid import UUID

from fastapi import APIRouter, Depends, Query

from finance_api.core.dependencies import get_income_category_service
from finance_api.schemas.income_categories import (
    IncomeCategoryCreate,
    IncomeCategoryResponse,
    IncomeCategoryUpdate,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.services.income_categories import IncomeCategoryService

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[IncomeCategoryResponse])
async def list_income_categories(
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(100, ge=1, le=1000, description="Tamanho da página"),
    service: IncomeCategoryService = Depends(get_income_category_service),
):
    """Lista todas as categorias de receitas com paginação."""
    items, total = await service.list(page, size)
    pages = (total + size - 1) // size if total > 0 else 0
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{category_id}", response_model=IncomeCategoryResponse)
async def get_income_category(
    category_id: UUID,
    service: IncomeCategoryService = Depends(get_income_category_service),
):
    """Busca uma categoria de receita por ID."""
    return await service.get_by_id(category_id)


@router.post("/", response_model=IncomeCategoryResponse, status_code=201)
async def create_income_category(
    category_data: IncomeCategoryCreate,
    service: IncomeCategoryService = Depends(get_income_category_service),
):
    """Cria uma nova categoria de receita."""
    return await service.create(category_data)


@router.put("/{category_id}", response_model=IncomeCategoryResponse)
async def update_income_category(
    category_id: UUID,
    update_data: IncomeCategoryUpdate,
    service: IncomeCategoryService = Depends(get_income_category_service),
):
    """Atualiza uma categoria de receita existente."""
    return await service.update(category_id, update_data)


@router.patch("/{category_id}", response_model=IncomeCategoryResponse)
async def patch_income_category(
    category_id: UUID,
    update_data: IncomeCategoryUpdate,
    service: IncomeCategoryService = Depends(get_income_category_service),
):
    """Atualiza parcialmente uma categoria de receita existente."""
    return await service.update(category_id, update_data)


@router.delete("/{category_id}", status_code=204)
async def delete_income_category(
    category_id: UUID,
    service: IncomeCategoryService = Depends(get_income_category_service),
):
    """Exclui uma categoria de receita."""
    await service.delete(category_id)
