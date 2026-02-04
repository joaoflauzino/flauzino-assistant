from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.categories import CategoryRepository
from finance_api.schemas.categories import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.services.categories import CategoryService

router = APIRouter()


def get_category_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryService:
    repo = CategoryRepository(db)
    return CategoryService(repo)


@router.get("/", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Page size"),
    service: CategoryService = Depends(get_category_service),
):
    """List all categories with pagination."""
    items, total = await service.list(page, size)
    pages = (total + size - 1) // size if total > 0 else 0
    return PaginatedResponse(
        items=items, total=total, page=page, size=size, pages=pages
    )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    service: CategoryService = Depends(get_category_service),
):
    """Get a category by ID."""
    category = await service.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    category_data: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
):
    """Create a new category."""
    try:
        return await service.create(category_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    update_data: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
):
    """Update an existing category."""
    try:
        category = await service.update(category_id, update_data)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    service: CategoryService = Depends(get_category_service),
):
    """Delete a category."""
    success = await service.delete(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
