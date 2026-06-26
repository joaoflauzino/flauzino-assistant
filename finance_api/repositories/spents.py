from datetime import date
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func, text, case, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.spents import Spent
from finance_api.schemas.spents import SpentCreate, SpentUpdate
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


class SpentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, spent: SpentCreate) -> Spent:
        new_spent = Spent(**spent.model_dump(exclude={"is_installment"}))
        self.db.add(new_spent)
        await self.db.commit()
        await self.db.refresh(new_spent)
        logger.info(f"Created spent: {new_spent.id}")
        return new_spent

    async def create_many(self, spents: List[Spent]) -> List[Spent]:
        self.db.add_all(spents)
        await self.db.commit()
        for s in spents:
            await self.db.refresh(s)
        logger.info(f"Created {len(spents)} spents")
        return spents

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> tuple[List[Spent], int]:
        query = select(Spent)

        # Convert UTC timestamp to Brazil timezone (America/Sao_Paulo) before extracting date
        # This ensures date filtering works correctly for Brazilian users (UTC-3)
        # Using AT TIME ZONE converts the timestamp to the specified timezone
        if start_date:
            query = query.where(
                func.date(Spent.created_at.op("AT TIME ZONE")("America/Sao_Paulo")) >= start_date
            )
        if end_date:
            query = query.where(
                func.date(Spent.created_at.op("AT TIME ZONE")("America/Sao_Paulo")) <= end_date
            )

        # Count query
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Pagination
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        logger.info(f"Listed {len(items)} spents")
        return items, total

    async def list_by_multiple_periods(
        self,
        periods: List[tuple[str, date, date]],
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[Spent], int]:
        query = select(Spent)

        conditions = []
        for pm_key, start_d, end_d in periods:
            condition = and_(
                Spent.payment_method == pm_key,
                func.date(Spent.created_at.op("AT TIME ZONE")("America/Sao_Paulo")) >= start_d,
                func.date(Spent.created_at.op("AT TIME ZONE")("America/Sao_Paulo")) <= end_d,
            )
            conditions.append(condition)

        if conditions:
            query = query.where(or_(*conditions))
        else:
            return [], 0

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def get_by_id(self, spent_id: UUID) -> Optional[Spent]:
        result = await self.db.execute(select(Spent).where(Spent.id == spent_id))
        spent = result.scalar_one_or_none()
        if spent:
            logger.info(f"Retrieved spent: {spent_id}")
        return spent

    async def get_installments_summary(self) -> List[dict]:
        """Get an aggregated summary of active installments."""
        query = (
            select(
                Spent.installment_id,
                func.min(Spent.category).label("category"),
                func.min(Spent.item_bought).label("item_bought"),
                func.min(Spent.amount).label("amount"),
                func.max(Spent.total_installments).label("total_installments"),
                func.max(
                    case((Spent.created_at <= func.now(), Spent.current_installment), else_=0)
                ).label("passed_installments"),
            )
            .where(Spent.installment_id.is_not(None))
            .group_by(Spent.installment_id)
            .order_by(text("passed_installments DESC"), text("total_installments DESC"))
        )

        result = await self.db.execute(query)
        rows = result.fetchall()

        return [
            {
                "installment_id": row.installment_id,
                "category": row.category,
                "item_bought": row.item_bought,
                "amount": row.amount,
                "total_installments": row.total_installments,
                "passed_installments": row.passed_installments,
            }
            for row in rows
        ]

    async def update(self, spent_id: UUID, update_data: SpentUpdate) -> Optional[Spent]:
        stmt = (
            update(Spent)
            .where(Spent.id == spent_id)
            .values(**update_data.model_dump(exclude_unset=True))
            .returning(Spent)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        logger.info(f"Updated spent: {spent_id}")
        return result.scalar_one_or_none()

    async def delete(self, spent_id: UUID) -> bool:
        stmt = delete(Spent).where(Spent.id == spent_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        if result.rowcount > 0:
            logger.info(f"Deleted spent: {spent_id}")
        return result.rowcount > 0
