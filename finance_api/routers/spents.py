from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.spents import SpentRepository
from finance_api.services.spents import SpentService
from finance_api.schemas.spents import SpentCreate, SpentResponse

router = APIRouter()


@router.post("/", response_model=SpentResponse)
async def create_spent(spent: SpentCreate, db: AsyncSession = Depends(get_db)):
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.create(spent)


@router.get("/", response_model=List[SpentResponse])
async def list_spents(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.list(skip, limit)
