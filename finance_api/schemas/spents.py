from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from finance_api.schemas.enums import CardEnum, CategoryEnum, NameEnum


class SpentBase(BaseModel):
    category: CategoryEnum
    amount: float
    payment_method: CardEnum
    payment_owner: NameEnum
    location: Optional[str] = None


class SpentCreate(SpentBase): ...


class SpentResponse(SpentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
