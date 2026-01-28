from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.spents import SpentRepository
from finance_api.schemas.spents import SpentCreate, SpentResponse

router = APIRouter()


@router.post("/", response_model=SpentResponse)
async def create_spent(spent: SpentCreate, db: AsyncSession = Depends(get_db)):
    repo = SpentRepository(db)
    try:
        return await repo.create(spent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[SpentResponse])
async def list_spents(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    repo = SpentRepository(db)
    return await repo.list(skip, limit)
