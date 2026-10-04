from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from finance_api.core.dependencies import get_income_service
from finance_api.schemas.incomes import (
    IncomeCreate,
    IncomeResponse,
    IncomeUpdate,
    MonthlyBalanceSummary,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.services.incomes import IncomeService

router = APIRouter()


@router.post("/", response_model=IncomeResponse, status_code=201)
async def create_income(
    income_data: IncomeCreate,
    service: IncomeService = Depends(get_income_service),
):
    """Registra uma nova receita."""
    return await service.create(income_data)


@router.get("/", response_model=PaginatedResponse[IncomeResponse])
async def list_incomes(
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(100, ge=1, le=1000, description="Tamanho da página"),
    start_date: Optional[date] = Query(None, description="Data inicial do filtro"),
    end_date: Optional[date] = Query(None, description="Data final do filtro"),
    category: Optional[str] = Query(None, description="Chave da categoria para filtro"),
    service: IncomeService = Depends(get_income_service),
):
    """Lista receitas com paginação e filtros opcionais por data e categoria."""
    items, total = await service.list(
        page=page,
        size=size,
        start_date=start_date,
        end_date=end_date,
        category=category,
    )
    pages = (total + size - 1) // size if total > 0 else 0
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/summary", response_model=MonthlyBalanceSummary)
async def get_monthly_summary(
    reference_month: Optional[str] = Query(
        None, description="Mês de referência no formato YYYY-MM (ex: '2026-08')"
    ),
    start_date: Optional[date] = Query(None, description="Data inicial do período"),
    end_date: Optional[date] = Query(None, description="Data final do período"),
    service: IncomeService = Depends(get_income_service),
):
    """Retorna o balanço mensal ou por período consolidado (receitas, despesas, saldo e taxa de economia)."""
    return await service.get_monthly_summary(
        reference_month=reference_month,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/{income_id}", response_model=IncomeResponse)
async def get_income(
    income_id: UUID,
    service: IncomeService = Depends(get_income_service),
):
    """Busca uma receita por ID."""
    return await service.get_by_id(income_id)


@router.put("/{income_id}", response_model=IncomeResponse)
async def update_income(
    income_id: UUID,
    update_data: IncomeUpdate,
    service: IncomeService = Depends(get_income_service),
):
    """Atualiza uma receita existente."""
    return await service.update(income_id, update_data)


@router.patch("/{income_id}", response_model=IncomeResponse)
async def patch_income(
    income_id: UUID,
    update_data: IncomeUpdate,
    service: IncomeService = Depends(get_income_service),
):
    """Atualiza parcialmente uma receita existente."""
    return await service.update(income_id, update_data)


@router.delete("/{income_id}", status_code=204)
async def delete_income(
    income_id: UUID,
    service: IncomeService = Depends(get_income_service),
):
    """Exclui uma receita."""
    await service.delete(income_id)
