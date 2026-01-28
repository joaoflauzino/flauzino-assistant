from pydantic import BaseModel, ConfigDict

from finance_api.schemas.enums import CategoryEnum


class SpendingLimitBase(BaseModel):
    category: CategoryEnum
    amount: float


class SpendingLimitCreate(SpendingLimitBase): ...


class SpendingLimitResponse(SpendingLimitBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
