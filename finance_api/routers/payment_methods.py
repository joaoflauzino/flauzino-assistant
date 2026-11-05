from uuid import UUID

from fastapi import APIRouter, Query

from finance_api.core.service_dependencies import PaymentMethodServiceDep
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.schemas.payment_methods import (
    PaymentMethodCreate,
    PaymentMethodResponse,
    PaymentMethodUpdate,
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[PaymentMethodResponse])
async def list_payment_methods(
    service: PaymentMethodServiceDep,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Page size"),
) -> PaginatedResponse[PaymentMethodResponse]:
    """List all payment methods with pagination."""
    items, total = await service.list(page, size)
    pages = (total + size - 1) // size if total > 0 else 0
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{method_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    method_id: UUID,
    service: PaymentMethodServiceDep,
) -> PaymentMethodResponse:
    """Get a payment method by ID."""
    return await service.get_by_id(method_id)


@router.post("/", response_model=PaymentMethodResponse, status_code=201)
async def create_payment_method(
    method_data: PaymentMethodCreate,
    service: PaymentMethodServiceDep,
) -> PaymentMethodResponse:
    """Create a new payment method."""
    return await service.create(method_data)


@router.put("/{method_id}", response_model=PaymentMethodResponse)
async def update_payment_method(
    method_id: UUID,
    update_data: PaymentMethodUpdate,
    service: PaymentMethodServiceDep,
) -> PaymentMethodResponse:
    """Update an existing payment method."""
    return await service.update(method_id, update_data)


@router.delete("/{method_id}", status_code=204)
async def delete_payment_method(
    method_id: UUID,
    service: PaymentMethodServiceDep,
) -> None:
    """Delete a payment method."""
    await service.delete(method_id)
