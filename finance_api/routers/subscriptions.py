from uuid import UUID

from fastapi import APIRouter, Response, status

from finance_api.core.subscription_dependencies import SubscriptionServiceDep
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.schemas.subscriptions import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
)

router = APIRouter()


@router.post("/", response_model=SubscriptionResponse)
async def create_subscription(
    subscription: SubscriptionCreate, service: SubscriptionServiceDep
) -> SubscriptionResponse:
    return await service.create(subscription)


@router.get("/", response_model=PaginatedResponse[SubscriptionResponse])
async def list_subscriptions(
    service: SubscriptionServiceDep,
    page: int = 1,
    size: int = 10,
    active_only: bool = False,
) -> PaginatedResponse[SubscriptionResponse]:
    return await service.list(page, size, active_only)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: UUID, service: SubscriptionServiceDep
) -> SubscriptionResponse:
    return await service.get_by_id(subscription_id)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: UUID,
    update_data: SubscriptionUpdate,
    service: SubscriptionServiceDep,
) -> SubscriptionResponse:
    return await service.update(subscription_id, update_data)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(subscription_id: UUID, service: SubscriptionServiceDep) -> Response:
    await service.delete(subscription_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
