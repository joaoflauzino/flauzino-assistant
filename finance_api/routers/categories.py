from uuid import UUID

from fastapi import APIRouter, Query

from finance_api.core.service_dependencies import CategoryServiceDep
from finance_api.schemas.categories import CategoryCreate, CategoryResponse, CategoryUpdate
from finance_api.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    service: CategoryServiceDep,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Page size"),
) -> PaginatedResponse[CategoryResponse]:
    """List all categories with pagination."""
    items, total = await service.list(page, size)
    pages = (total + size - 1) // size if total > 0 else 0
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    service: CategoryServiceDep,
) -> CategoryResponse:
    """Get a category by ID."""
    return await service.get_by_id(category_id)


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    category_data: CategoryCreate,
    service: CategoryServiceDep,
) -> CategoryResponse:
    """Create a new category."""
    return await service.create(category_data)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    update_data: CategoryUpdate,
    service: CategoryServiceDep,
) -> CategoryResponse:
    """Update an existing category."""
    return await service.update(category_id, update_data)


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    service: CategoryServiceDep,
) -> None:
    """Delete a category."""
    await service.delete(category_id)
