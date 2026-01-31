from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from finance_api.schemas.enums import CardEnum, CategoryEnum, NameEnum


class SpentBase(BaseModel):
    category: CategoryEnum
    amount: float
    payment_method: CardEnum
    payment_owner: NameEnum
    location: str


class SpentCreate(SpentBase): ...


class SpentUpdate(BaseModel):
    category: Optional[CategoryEnum] = None
    amount: Optional[float] = None
    payment_method: Optional[CardEnum] = None
    payment_owner: Optional[NameEnum] = None
    location: Optional[str] = None


class SpentResponse(SpentBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
