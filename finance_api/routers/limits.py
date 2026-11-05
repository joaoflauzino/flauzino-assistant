from datetime import date
from uuid import UUID

from fastapi import APIRouter, Response, status

from finance_api.core.service_dependencies import BalanceServiceDep, SpendingLimitServiceDep
from finance_api.schemas.limits import (
    CategoryBalance,
    SpendingLimitCreate,
    SpendingLimitResponse,
    SpendingLimitUpdate,
)
from finance_api.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.post("/", response_model=SpendingLimitResponse, status_code=status.HTTP_201_CREATED)
async def create_limit(
    limit_data: SpendingLimitCreate,
    service: SpendingLimitServiceDep,
) -> SpendingLimitResponse:
    return await service.create(limit_data)


@router.get("/", response_model=PaginatedResponse[SpendingLimitResponse])
async def list_limits(
    service: SpendingLimitServiceDep,
    page: int = 1,
    size: int = 10,
    start_date: date | None = None,
    end_date: date | None = None,
) -> PaginatedResponse[SpendingLimitResponse]:
    return await service.list(page, size, start_date, end_date)


@router.get("/balance", response_model=list[CategoryBalance])
async def get_balance(
    service: BalanceServiceDep,
    reference_month: str | None = None,
    categories: str | None = None,
) -> list[CategoryBalance]:
    category_list = [c.strip().lower() for c in categories.split(",")] if categories else None
    return await service.get_balance(reference_month=reference_month, categories=category_list)


@router.get("/{limit_id}", response_model=SpendingLimitResponse)
async def get_limit(limit_id: UUID, service: SpendingLimitServiceDep) -> SpendingLimitResponse:
    return await service.get_by_id(limit_id)


@router.patch("/{limit_id}", response_model=SpendingLimitResponse)
async def update_limit(
    limit_id: UUID,
    update_data: SpendingLimitUpdate,
    service: SpendingLimitServiceDep,
) -> SpendingLimitResponse:
    return await service.update(limit_id, update_data)


@router.delete("/{limit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_limit(limit_id: UUID, service: SpendingLimitServiceDep) -> Response:
    await service.delete(limit_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
