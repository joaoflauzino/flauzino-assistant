import builtins
from datetime import date
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.logger import get_logger
from finance_api.models.incomes import Income
from finance_api.schemas.incomes import IncomeCreate, IncomeUpdate

logger = get_logger(__name__)


class IncomeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, income_data: IncomeCreate) -> Income:
        payload = income_data.model_dump(exclude_unset=True)
        new_income = Income(**payload)
        self.db.add(new_income)
        await self.db.commit()
        await self.db.refresh(new_income)
        logger.info(f"Created income: {new_income.id}")
        return new_income

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
        category: str | None = None,
    ) -> tuple[list[Income], int]:
        effective_date = func.coalesce(
            Income.competence_date,
            func.date(Income.received_at.op("AT TIME ZONE")("America/Sao_Paulo")),
        )
        query = select(Income)

        if start_date:
            query = query.where(effective_date >= start_date)
        if end_date:
            query = query.where(effective_date <= end_date)
        if category:
            query = query.where(Income.category == category)

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = (
            query.order_by(effective_date.desc(), Income.received_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        logger.info(f"Listed {len(items)} incomes")
        return items, total

    async def list_by_period(self, start_date: date, end_date: date) -> builtins.list[Income]:
        effective_date = func.coalesce(
            Income.competence_date,
            func.date(Income.received_at.op("AT TIME ZONE")("America/Sao_Paulo")),
        )
        query = (
            select(Income)
            .where(
                effective_date >= start_date,
                effective_date <= end_date,
            )
            .order_by(effective_date.desc(), Income.received_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, income_id: UUID) -> Income | None:
        result = await self.db.execute(select(Income).where(Income.id == income_id))
        income = result.scalar_one_or_none()
        if income:
            logger.info(f"Retrieved income: {income_id}")
        return income

    async def update(self, income_id: UUID, update_data: IncomeUpdate) -> Income | None:
        stmt = (
            update(Income)
            .where(Income.id == income_id)
            .values(**update_data.model_dump(exclude_unset=True))
            .returning(Income)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        logger.info(f"Updated income: {income_id}")
        return result.scalar_one_or_none()

    async def delete(self, income_id: UUID) -> bool:
        stmt = delete(Income).where(Income.id == income_id)
        result = cast(CursorResult[Any], await self.db.execute(stmt))
        await self.db.commit()
        if result.rowcount > 0:
            logger.info(f"Deleted income: {income_id}")
        return result.rowcount > 0
