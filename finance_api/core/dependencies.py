from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.database import get_db
from finance_api.repositories.categories import CategoryRepository
from finance_api.repositories.invoices import InvoiceRepository
from finance_api.repositories.limits import SpendingLimitRepository
from finance_api.repositories.payment_methods import PaymentMethodRepository
from finance_api.repositories.spents import SpentRepository
from finance_api.services.balances import BalanceService
from finance_api.services.invoices import InvoiceService
from finance_api.services.limits import SpendingLimitService
from finance_api.services.spents import SpentService


def get_balance_service(db: AsyncSession = Depends(get_db)) -> BalanceService:
    """FastAPI dependency provider for BalanceService."""
    pm_repo = PaymentMethodRepository(db)
    inv_repo = InvoiceRepository(db)
    return BalanceService(
        limit_repo=SpendingLimitRepository(db),
        spent_repo=SpentRepository(db),
        category_repo=CategoryRepository(db),
        pm_repo=pm_repo,
        inv_service=InvoiceService(inv_repo, pm_repo),
    )


def get_spending_limit_service(db: AsyncSession = Depends(get_db)) -> SpendingLimitService:
    """FastAPI dependency provider for SpendingLimitService."""
    return SpendingLimitService(
        repo=SpendingLimitRepository(db),
        category_repo=CategoryRepository(db),
    )


def get_spent_service(db: AsyncSession = Depends(get_db)) -> SpentService:
    """FastAPI dependency provider for SpentService."""
    pm_repo = PaymentMethodRepository(db)
    inv_repo = InvoiceRepository(db)
    return SpentService(
        repo=SpentRepository(db),
        category_repo=CategoryRepository(db),
        pm_repo=pm_repo,
        inv_service=InvoiceService(inv_repo, pm_repo),
    )
