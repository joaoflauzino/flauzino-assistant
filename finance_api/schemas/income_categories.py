from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncomeCategoryBase(BaseModel):
    key: str = Field(
        ..., max_length=50, description="Unique identifier key for the income category"
    )
    display_name: str = Field(..., max_length=100, description="Human-readable display name")


class IncomeCategoryCreate(IncomeCategoryBase): ...


class IncomeCategoryUpdate(BaseModel):
    key: str | None = Field(None, max_length=50)
    display_name: str | None = Field(None, max_length=100)


class IncomeCategoryResponse(IncomeCategoryBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
