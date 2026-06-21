from uuid import UUID

from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.subscriptions import SubscriptionRepository
from finance_api.services.subscriptions import SubscriptionService
from finance_api.schemas.subscriptions import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from finance_api.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.post("/", response_model=SubscriptionResponse)
async def create_subscription(
    subscription: SubscriptionCreate, db: AsyncSession = Depends(get_db)
) -> SubscriptionResponse:
    repo = SubscriptionRepository(db)
    service = SubscriptionService(repo)
    return await service.create(subscription)


@router.get("/", response_model=PaginatedResponse[SubscriptionResponse])
async def list_subscriptions(
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SubscriptionResponse]:
    repo = SubscriptionRepository(db)
    service = SubscriptionService(repo)
    return await service.list(page, size, active_only)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: UUID, db: AsyncSession = Depends(get_db)
) -> SubscriptionResponse:
    repo = SubscriptionRepository(db)
    service = SubscriptionService(repo)
    return await service.get_by_id(subscription_id)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: UUID, update_data: SubscriptionUpdate, db: AsyncSession = Depends(get_db)
) -> SubscriptionResponse:
    repo = SubscriptionRepository(db)
    service = SubscriptionService(repo)
    return await service.update(subscription_id, update_data)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: UUID, db: AsyncSession = Depends(get_db)
) -> Response:
    repo = SubscriptionRepository(db)
    service = SubscriptionService(repo)
    await service.delete(subscription_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
