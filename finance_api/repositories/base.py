from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyRepository[T, ID]:
    """Generic reusable SQLAlchemy 2.0 async repository."""

    model: type[T]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, entity_id: ID) -> T | None:
        return await self.db.get(self.model, entity_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add(self, entity: T) -> T:
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def delete_entity(self, entity: T) -> None:
        await self.db.delete(entity)
        await self.db.commit()
