from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.services.limits import SpendingLimitService
from finance_api.schemas.limits import SpendingLimitCreate, SpendingLimitResponse

router = APIRouter()


@router.post("/", response_model=SpendingLimitResponse)
async def create_or_update_limit(
    limit_data: SpendingLimitCreate, db: AsyncSession = Depends(get_db)
):
    repo = SpendingLimitRepository(db)
    service = SpendingLimitService(repo)
    return await service.create_or_update(limit_data)


@router.get("/", response_model=List[SpendingLimitResponse])
async def list_limits(db: AsyncSession = Depends(get_db)):
    repo = SpendingLimitRepository(db)
    service = SpendingLimitService(repo)
    return await service.list()
