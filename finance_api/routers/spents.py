from datetime import date
from uuid import UUID

from fastapi import APIRouter, Response, status

from finance_api.core.service_dependencies import SpentServiceDep
from finance_api.schemas.installments import InstallmentSummary
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.schemas.spents import DashboardMode, SpentCreate, SpentResponse, SpentUpdate

router = APIRouter()


@router.post("/", response_model=SpentResponse)
async def create_spent(spent: SpentCreate, service: SpentServiceDep) -> SpentResponse:
    return await service.create(spent)


@router.get("/", response_model=PaginatedResponse[SpentResponse])
async def list_spents(
    service: SpentServiceDep,
    page: int = 1,
    size: int = 10,
    start_date: date | None = None,
    end_date: date | None = None,
) -> PaginatedResponse[SpentResponse]:
    return await service.list(page, size, start_date, end_date)


@router.get("/dashboard", response_model=PaginatedResponse[SpentResponse])
async def get_dashboard(
    service: SpentServiceDep,
    reference_month: str,
    mode: DashboardMode = DashboardMode.CIVIL_MONTH,
    page: int = 1,
    size: int = 100,
) -> PaginatedResponse[SpentResponse]:
    return await service.get_dashboard(reference_month, mode.value, page, size)


@router.get("/installments-summary", response_model=list[InstallmentSummary])
async def get_installments_summary(
    service: SpentServiceDep,
) -> list[InstallmentSummary]:
    return await service.get_installments_summary()


@router.get("/{spent_id}", response_model=SpentResponse)
async def get_spent(spent_id: UUID, service: SpentServiceDep) -> SpentResponse:
    return await service.get_by_id(spent_id)


@router.patch("/{spent_id}", response_model=SpentResponse)
async def update_spent(
    spent_id: UUID,
    update_data: SpentUpdate,
    service: SpentServiceDep,
) -> SpentResponse:
    return await service.update(spent_id, update_data)


@router.delete("/{spent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spent(spent_id: UUID, service: SpentServiceDep) -> Response:
    await service.delete(spent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
