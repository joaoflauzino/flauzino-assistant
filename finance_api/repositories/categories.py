from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.categories import Category
from finance_api.schemas.categories import CategoryCreate, CategoryUpdate
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


class CategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, category_data: CategoryCreate) -> Category:
        new_category = Category(**category_data.model_dump())
        self.db.add(new_category)
        await self.db.commit()
        await self.db.refresh(new_category)
        logger.info(f"Created category: {new_category.key}")
        return new_category

    async def list(self, skip: int = 0, limit: int = 100) -> tuple[List[Category], int]:
        query = select(Category).order_by(Category.display_name)

        # Count query
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Pagination
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        logger.info(f"Listed {len(items)} categories")
        return items, total

    async def get_by_id(self, category_id: UUID) -> Optional[Category]:
        result = await self.db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        if category:
            logger.info(f"Retrieved category: {category_id}")
        return category

    async def get_by_key(self, key: str) -> Optional[Category]:
        result = await self.db.execute(select(Category).where(Category.key == key))
        return result.scalar_one_or_none()

    async def update(
        self, category_id: UUID, update_data: CategoryUpdate
    ) -> Optional[Category]:
        stmt = (
            update(Category)
            .where(Category.id == category_id)
            .values(**update_data.model_dump(exclude_unset=True))
            .returning(Category)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        logger.info(f"Updated category: {category_id}")
        return result.scalar_one_or_none()

    async def delete(self, category_id: UUID) -> bool:
        stmt = delete(Category).where(Category.id == category_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        if result.rowcount > 0:
            logger.info(f"Deleted category: {category_id}")
        return result.rowcount > 0
