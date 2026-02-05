from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.payment_owners import PaymentOwnerRepository
from finance_api.schemas.payment_owners import (
    PaymentOwnerCreate,
    PaymentOwnerUpdate,
    PaymentOwnerResponse,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.services.payment_owners import PaymentOwnerService

router = APIRouter()


def get_payment_owner_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentOwnerService:
    repo = PaymentOwnerRepository(db)
    return PaymentOwnerService(repo)


@router.get("/", response_model=PaginatedResponse[PaymentOwnerResponse])
async def list_payment_owners(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Page size"),
    service: PaymentOwnerService = Depends(get_payment_owner_service),
):
    """List all payment owners with pagination."""
    items, total = await service.list(page, size)
    pages = (total + size - 1) // size if total > 0 else 0
    return PaginatedResponse(
        items=items, total=total, page=page, size=size, pages=pages
    )


@router.get("/{owner_id}", response_model=PaymentOwnerResponse)
async def get_payment_owner(
    owner_id: UUID,
    service: PaymentOwnerService = Depends(get_payment_owner_service),
):
    """Get a payment owner by ID."""
    return await service.get_by_id(owner_id)


@router.post("/", response_model=PaymentOwnerResponse, status_code=201)
async def create_payment_owner(
    owner_data: PaymentOwnerCreate,
    service: PaymentOwnerService = Depends(get_payment_owner_service),
):
    """Create a new payment owner."""
    return await service.create(owner_data)


@router.put("/{owner_id}", response_model=PaymentOwnerResponse)
async def update_payment_owner(
    owner_id: UUID,
    update_data: PaymentOwnerUpdate,
    service: PaymentOwnerService = Depends(get_payment_owner_service),
):
    """Update an existing payment owner."""
    return await service.update(owner_id, update_data)


@router.delete("/{owner_id}", status_code=204)
async def delete_payment_owner(
    owner_id: UUID,
    service: PaymentOwnerService = Depends(get_payment_owner_service),
):
    """Delete a payment owner."""
    await service.delete(owner_id)
