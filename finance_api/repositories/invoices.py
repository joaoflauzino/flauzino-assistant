from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.invoices import Invoice
from finance_api.schemas.invoices import InvoiceCreate, InvoiceUpdate
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


class InvoiceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, invoice: InvoiceCreate) -> Invoice:
        new_invoice = Invoice(**invoice.model_dump())
        self.db.add(new_invoice)
        await self.db.commit()
        await self.db.refresh(new_invoice)
        logger.info(
            f"Created invoice for {new_invoice.payment_method_key} - {new_invoice.reference_month}"
        )
        return new_invoice

    async def get_by_id(self, invoice_id: UUID) -> Optional[Invoice]:
        result = await self.db.execute(select(Invoice).where(Invoice.id == invoice_id))
        return result.scalar_one_or_none()

    async def get_by_payment_method_and_month(
        self, payment_method_key: str, reference_month: str
    ) -> Optional[Invoice]:
        query = select(Invoice).where(
            Invoice.payment_method_key == payment_method_key,
            Invoice.reference_month == reference_month,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_month(self, reference_month: str) -> List[Invoice]:
        query = select(Invoice).where(Invoice.reference_month == reference_month)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, invoice_id: UUID, update_data: InvoiceUpdate) -> Optional[Invoice]:
        stmt = (
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(**update_data.model_dump(exclude_unset=True))
            .returning(Invoice)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()
