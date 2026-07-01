import asyncio
from finance_api.repositories.spents import SpentRepository
from finance_api.core.db import async_session
from sqlalchemy import select
from finance_api.models.spents import Spent

async def main():
    async with async_session() as db:
        repo = SpentRepository(db)
        result = await db.execute(select(Spent).limit(1))
        spent = result.scalars().first()
        if spent:
            print("Spent found:", spent.id, spent.item_bought)
            deleted = await repo.delete(spent.id)
            print("Deleted:", deleted)
        else:
            print("No spents found.")

asyncio.run(main())
