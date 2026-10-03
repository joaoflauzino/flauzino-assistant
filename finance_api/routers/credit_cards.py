from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.accounts import AccountRepository
from finance_api.repositories.credit_cards import CreditCardRepository
from finance_api.schemas.credit_cards import (
    CreditCardCreate,
    CreditCardResponse,
    CreditCardUpdate,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.services.credit_cards import CreditCardService

router = APIRouter()


def get_credit_card_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CreditCardService:
    repo = CreditCardRepository(db)
    account_repo = AccountRepository(db)
    return CreditCardService(repository=repo, account_repository=account_repo)


@router.get("/", response_model=PaginatedResponse[CreditCardResponse])
async def list_credit_cards(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Page size"),
    account_id: Optional[UUID] = Query(None, description="Filter by account ID"),
    service: CreditCardService = Depends(get_credit_card_service),
):
    """List all credit cards with pagination and optional account filter."""
    items, total = await service.list(page=page, size=size, account_id=account_id)
    pages = (total + size - 1) // size if total > 0 else 0
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{card_id}", response_model=CreditCardResponse)
async def get_credit_card(
    card_id: UUID,
    service: CreditCardService = Depends(get_credit_card_service),
):
    """Get a credit card by ID."""
    return await service.get_by_id(card_id)


@router.post("/", response_model=CreditCardResponse, status_code=201)
async def create_credit_card(
    card_data: CreditCardCreate,
    service: CreditCardService = Depends(get_credit_card_service),
):
    """Create a new credit card."""
    return await service.create(card_data)


@router.put("/{card_id}", response_model=CreditCardResponse)
async def update_credit_card(
    card_id: UUID,
    update_data: CreditCardUpdate,
    service: CreditCardService = Depends(get_credit_card_service),
):
    """Update an existing credit card."""
    return await service.update(card_id, update_data)


@router.delete("/{card_id}", status_code=204)
async def delete_credit_card(
    card_id: UUID,
    service: CreditCardService = Depends(get_credit_card_service),
):
    """Delete a credit card."""
    await service.delete(card_id)
