from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from finance_api.schemas.enums import CategoryEnum


class SpendingLimitBase(BaseModel):
    category: CategoryEnum
    amount: float


class SpendingLimitCreate(SpendingLimitBase): ...


class SpendingLimitUpdate(BaseModel):
    category: Optional[CategoryEnum] = None
    amount: Optional[float] = None


class SpendingLimitResponse(SpendingLimitBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
