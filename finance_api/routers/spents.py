from uuid import UUID

from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.spents import SpentRepository
from finance_api.services.spents import SpentService
from finance_api.schemas.spents import SpentCreate, SpentResponse, SpentUpdate
from finance_api.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.post("/", response_model=SpentResponse)
async def create_spent(
    spent: SpentCreate, db: AsyncSession = Depends(get_db)
) -> SpentResponse:
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.create(spent)


@router.get("/", response_model=PaginatedResponse[SpentResponse])
async def list_spents(
    page: int = 1, size: int = 10, db: AsyncSession = Depends(get_db)
) -> PaginatedResponse[SpentResponse]:
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.list(page, size)


@router.get("/{spent_id}", response_model=SpentResponse)
async def get_spent(
    spent_id: UUID, db: AsyncSession = Depends(get_db)
) -> SpentResponse:
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.get_by_id(spent_id)


@router.patch("/{spent_id}", response_model=SpentResponse)
async def update_spent(
    spent_id: UUID, update_data: SpentUpdate, db: AsyncSession = Depends(get_db)
) -> SpentResponse:
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.update(spent_id, update_data)


@router.delete("/{spent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spent(spent_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    repo = SpentRepository(db)
    service = SpentService(repo)
    await service.delete(spent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
