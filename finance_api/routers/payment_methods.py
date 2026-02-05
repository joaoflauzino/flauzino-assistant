from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.schemas.payment_methods import (
    PaymentMethodCreate,
    PaymentMethodUpdate,
    PaymentMethodResponse,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.services.payment_methods import PaymentMethodService

router = APIRouter()


def get_payment_method_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentMethodService:
    repo = PaymentMethodRepository(db)
    return PaymentMethodService(repo)


@router.get("/", response_model=PaginatedResponse[PaymentMethodResponse])
async def list_payment_methods(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Page size"),
    service: PaymentMethodService = Depends(get_payment_method_service),
):
    """List all payment methods with pagination."""
    items, total = await service.list(page, size)
    pages = (total + size - 1) // size if total > 0 else 0
    return PaginatedResponse(
        items=items, total=total, page=page, size=size, pages=pages
    )


@router.get("/{method_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    method_id: UUID,
    service: PaymentMethodService = Depends(get_payment_method_service),
):
    """Get a payment method by ID."""
    return await service.get_by_id(method_id)


@router.post("/", response_model=PaymentMethodResponse, status_code=201)
async def create_payment_method(
    method_data: PaymentMethodCreate,
    service: PaymentMethodService = Depends(get_payment_method_service),
):
    """Create a new payment method."""
    return await service.create(method_data)


@router.put("/{method_id}", response_model=PaymentMethodResponse)
async def update_payment_method(
    method_id: UUID,
    update_data: PaymentMethodUpdate,
    service: PaymentMethodService = Depends(get_payment_method_service),
):
    """Update an existing payment method."""
    return await service.update(method_id, update_data)


@router.delete("/{method_id}", status_code=204)
async def delete_payment_method(
    method_id: UUID,
    service: PaymentMethodService = Depends(get_payment_method_service),
):
    """Delete a payment method."""
    await service.delete(method_id)
