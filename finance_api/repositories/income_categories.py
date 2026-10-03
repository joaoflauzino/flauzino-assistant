import unicodedata
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.logger import get_logger
from finance_api.models.income_categories import IncomeCategory
from finance_api.schemas.income_categories import IncomeCategoryCreate, IncomeCategoryUpdate

logger = get_logger(__name__)


def _normalize_str(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


class IncomeCategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, category_data: IncomeCategoryCreate) -> IncomeCategory:
        new_category = IncomeCategory(**category_data.model_dump())
        self.db.add(new_category)
        await self.db.commit()
        await self.db.refresh(new_category)
        logger.info(f"Created income category: {new_category.key}")
        return new_category

    async def list(self, skip: int = 0, limit: int = 100) -> tuple[List[IncomeCategory], int]:
        query = select(IncomeCategory).order_by(IncomeCategory.display_name)

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        logger.info(f"Listed {len(items)} income categories")
        return items, total

    async def get_by_id(self, category_id: UUID) -> Optional[IncomeCategory]:
        result = await self.db.execute(
            select(IncomeCategory).where(IncomeCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        if category:
            logger.info(f"Retrieved income category: {category_id}")
        return category

    async def get_by_key(self, key: str) -> Optional[IncomeCategory]:
        # Exact match first
        result = await self.db.execute(select(IncomeCategory).where(IncomeCategory.key == key))
        category = result.scalar_one_or_none()
        if category:
            return category

        # Fallback to normalized match (e.g. 'salário' matching 'salario')
        normalized_target = _normalize_str(key)
        all_cats_result = await self.db.execute(select(IncomeCategory))
        for cat in all_cats_result.scalars().all():
            if (
                _normalize_str(cat.key) == normalized_target
                or _normalize_str(cat.display_name) == normalized_target
            ):
                return cat

        return None

    async def update(
        self, category_id: UUID, update_data: IncomeCategoryUpdate
    ) -> Optional[IncomeCategory]:
        stmt = (
            update(IncomeCategory)
            .where(IncomeCategory.id == category_id)
            .values(**update_data.model_dump(exclude_unset=True))
            .returning(IncomeCategory)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        logger.info(f"Updated income category: {category_id}")
        return result.scalar_one_or_none()

    async def delete(self, category_id: UUID) -> bool:
        stmt = delete(IncomeCategory).where(IncomeCategory.id == category_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        if result.rowcount > 0:
            logger.info(f"Deleted income category: {category_id}")
        return result.rowcount > 0
