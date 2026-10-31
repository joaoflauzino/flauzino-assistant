from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.import_batches import ImportBatch
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.repositories.base import RepositoryProtocol, SQLAlchemyRepository


class ImportBatchRepositoryProtocol(RepositoryProtocol[ImportBatch, UUID], Protocol):
    """Domain repository contract for ImportBatch persistence."""

    async def create(self, batch: ImportBatch) -> ImportBatch: ...

    async def update_batch_stats(
        self,
        batch: ImportBatch,
        possible_duplicates: int,
        ai_used: bool,
    ) -> ImportBatch: ...

    async def get_by_sha256(self, sha256_hash: str) -> ImportBatch | None: ...

    async def list_all(self, limit: int = 50) -> Sequence[ImportBatch]: ...

    async def get_counts_by_status(self, batch_id: UUID) -> dict[str, int]: ...

    async def get_global_summary(self) -> dict[str, int]: ...


class ImportBatchRepository(SQLAlchemyRepository[ImportBatch, UUID]):
    model = ImportBatch

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def create(self, batch: ImportBatch) -> ImportBatch:
        return await self.add(batch)

    async def update_batch_stats(
        self,
        batch: ImportBatch,
        possible_duplicates: int,
        ai_used: bool,
    ) -> ImportBatch:
        batch.possible_duplicates = possible_duplicates
        batch.ai_used = ai_used
        return await self.add(batch)

    async def get_by_id(self, batch_id: UUID) -> ImportBatch | None:
        result = await self.db.execute(select(ImportBatch).where(ImportBatch.id == batch_id))
        return result.scalar_one_or_none()

    async def get_by_sha256(self, sha256_hash: str) -> ImportBatch | None:
        result = await self.db.execute(
            select(ImportBatch).where(ImportBatch.file_sha256 == sha256_hash)
        )
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 50) -> Sequence[ImportBatch]:
        result = await self.db.execute(
            select(ImportBatch).order_by(desc(ImportBatch.created_at)).limit(limit)
        )
        return result.scalars().all()

    async def get_counts_by_status(self, batch_id: UUID) -> dict[str, int]:
        stmt = (
            select(StagedTransaction.status, func.count(StagedTransaction.id))
            .where(StagedTransaction.batch_id == batch_id)
            .group_by(StagedTransaction.status)
        )
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        counts = {"pending": 0, "approved": 0, "committed": 0, "ignored": 0, "linked": 0}
        for status_val, count in rows:
            key = str(status_val).lower()
            counts[key] = count
        return counts

    async def get_global_summary(self) -> dict[str, int]:
        stmt = (
            select(StagedTransaction.status, func.count(StagedTransaction.id))
            .where(StagedTransaction.status.in_(["PENDING", "APPROVED"]))
            .group_by(StagedTransaction.status)
        )
        result = await self.db.execute(stmt)
        counts = {"pending": 0, "approved": 0}
        for status_val, count in result.fetchall():
            key = str(status_val).lower()
            counts[key] = count
        return counts
