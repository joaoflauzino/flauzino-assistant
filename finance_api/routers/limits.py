from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.services.limits import SpendingLimitService
from finance_api.schemas.limits import (
    SpendingLimitCreate,
    SpendingLimitResponse,
    SpendingLimitUpdate,
)
from finance_api.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.post(
    "/", response_model=SpendingLimitResponse, status_code=status.HTTP_201_CREATED
)
async def create_limit(
    limit_data: SpendingLimitCreate, db: AsyncSession = Depends(get_db)
) -> SpendingLimitResponse:
    repo = SpendingLimitRepository(db)
    service = SpendingLimitService(repo)
    return await service.create(limit_data)


@router.get("/", response_model=PaginatedResponse[SpendingLimitResponse])
async def list_limits(
    page: int = 1, size: int = 10, db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[SpendingLimitResponse]:
    repo = SpendingLimitRepository(db)
    service = SpendingLimitService(repo)
    return await service.list(page, size)


@router.get("/{limit_id}", response_model=SpendingLimitResponse)
async def get_limit(
    limit_id: UUID, db: AsyncSession = Depends(get_db)
) -> SpendingLimitResponse:
    repo = SpendingLimitRepository(db)
    service = SpendingLimitService(repo)
    return await service.get_by_id(limit_id)


@router.patch("/{limit_id}", response_model=SpendingLimitResponse)
async def update_limit(
    limit_id: UUID, update_data: SpendingLimitUpdate, db: AsyncSession = Depends(get_db)
) -> SpendingLimitResponse:
    repo = SpendingLimitRepository(db)
    service = SpendingLimitService(repo)
    return await service.update(limit_id, update_data)


@router.delete("/{limit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_limit(limit_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    repo = SpendingLimitRepository(db)
    service = SpendingLimitService(repo)
    await service.delete(limit_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
