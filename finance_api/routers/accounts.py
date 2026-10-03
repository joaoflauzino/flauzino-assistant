from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.accounts import AccountRepository
from finance_api.schemas.accounts import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
)
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.services.accounts import AccountService

router = APIRouter()


def get_account_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountService:
    repo = AccountRepository(db)
    return AccountService(repo)


@router.get("/", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Page size"),
    owner: Optional[str] = Query(None, description="Filter by owner"),
    service: AccountService = Depends(get_account_service),
):
    """List all accounts with pagination and optional owner filter."""
    items, total = await service.list(page=page, size=size, owner=owner)
    pages = (total + size - 1) // size if total > 0 else 0
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    service: AccountService = Depends(get_account_service),
):
    """Get an account by ID."""
    return await service.get_by_id(account_id)


@router.post("/", response_model=AccountResponse, status_code=201)
async def create_account(
    account_data: AccountCreate,
    service: AccountService = Depends(get_account_service),
):
    """Create a new account."""
    return await service.create(account_data)


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    update_data: AccountUpdate,
    service: AccountService = Depends(get_account_service),
):
    """Update an existing account."""
    return await service.update(account_id, update_data)


@router.delete("/{account_id}", status_code=204)
async def delete_account(
    account_id: UUID,
    service: AccountService = Depends(get_account_service),
):
    """Delete an account."""
    await service.delete(account_id)
