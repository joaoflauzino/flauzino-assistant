from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class CategoryBase(BaseModel):
    key: str = Field(
        ..., max_length=50, description="Unique identifier key for the category"
    )
    display_name: str = Field(
        ..., max_length=100, description="Human-readable display name"
    )


class CategoryCreate(CategoryBase): ...


class CategoryUpdate(BaseModel):
    key: str | None = Field(None, max_length=50)
    display_name: str | None = Field(None, max_length=100)


class CategoryResponse(CategoryBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
