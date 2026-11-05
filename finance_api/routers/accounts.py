from uuid import UUID

from fastapi import APIRouter, Query

from finance_api.core.service_dependencies import AccountServiceDep
from finance_api.schemas.accounts import AccountCreate, AccountResponse, AccountUpdate
from finance_api.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    service: AccountServiceDep,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(100, ge=1, le=1000, description="Page size"),
    owner: str | None = Query(None, description="Filter by owner"),
) -> PaginatedResponse[AccountResponse]:
    """List all accounts with pagination and optional owner filter."""
    items, total = await service.list(page=page, size=size, owner=owner)
    pages = (total + size - 1) // size if total > 0 else 0
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    service: AccountServiceDep,
) -> AccountResponse:
    """Get an account by ID."""
    return await service.get_by_id(account_id)


@router.post("/", response_model=AccountResponse, status_code=201)
async def create_account(
    account_data: AccountCreate,
    service: AccountServiceDep,
) -> AccountResponse:
    """Create a new account."""
    return await service.create(account_data)


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    update_data: AccountUpdate,
    service: AccountServiceDep,
) -> AccountResponse:
    """Update an existing account."""
    return await service.update(account_id, update_data)


@router.delete("/{account_id}", status_code=204)
async def delete_account(
    account_id: UUID,
    service: AccountServiceDep,
) -> None:
    """Delete an account."""
    await service.delete(account_id)
