from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.spents import SpentRepository
from finance_api.services.spents import SpentService
from finance_api.repositories.invoices import InvoiceRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.services.invoices import InvoiceService
from finance_api.schemas.spents import SpentCreate, SpentResponse, SpentUpdate, DashboardMode
from finance_api.schemas.pagination import PaginatedResponse
from finance_api.schemas.installments import InstallmentSummary

router = APIRouter()


@router.post("/", response_model=SpentResponse)
async def create_spent(spent: SpentCreate, db: AsyncSession = Depends(get_db)) -> SpentResponse:
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.create(spent)


@router.get("/", response_model=PaginatedResponse[SpentResponse])
async def list_spents(
    page: int = 1,
    size: int = 10,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SpentResponse]:
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.list(page, size, start_date, end_date)


@router.get("/dashboard", response_model=PaginatedResponse[SpentResponse])
async def get_dashboard(
    reference_month: str,
    mode: DashboardMode = DashboardMode.CIVIL_MONTH,
    page: int = 1,
    size: int = 100,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SpentResponse]:
    repo = SpentRepository(db)
    service = SpentService(repo)

    inv_repo = InvoiceRepository(db)
    pm_repo = PaymentMethodRepository(db)
    inv_service = InvoiceService(inv_repo, pm_repo)

    return await service.get_dashboard(
        reference_month, mode.value, page, size, inv_service, pm_repo
    )


@router.get("/installments-summary", response_model=list[InstallmentSummary])
async def get_installments_summary(db: AsyncSession = Depends(get_db)) -> list[InstallmentSummary]:
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.get_installments_summary()


@router.get("/{spent_id}", response_model=SpentResponse)
async def get_spent(spent_id: UUID, db: AsyncSession = Depends(get_db)) -> SpentResponse:
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.get_by_id(spent_id)


@router.patch("/{spent_id}", response_model=SpentResponse)
async def update_spent(
    spent_id: UUID, update_data: SpentUpdate, db: AsyncSession = Depends(get_db)
) -> SpentResponse:
    repo = SpentRepository(db)
    service = SpentService(repo)
    return await service.update(spent_id, update_data)


@router.delete("/{spent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spent(spent_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    repo = SpentRepository(db)
    service = SpentService(repo)
    await service.delete(spent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
