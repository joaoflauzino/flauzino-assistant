from datetime import date, timedelta
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.incomes import Income
from finance_api.models.spents import Spent
from finance_api.models.staged_transactions import StagedTransaction


class StagedTransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tx_id: UUID) -> StagedTransaction | None:
        query = select(StagedTransaction).where(StagedTransaction.id == tx_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_existing_fingerprints(self, fps: list[str]) -> set[str]:
        if not fps:
            return set()
        query = select(StagedTransaction.fingerprint).where(StagedTransaction.fingerprint.in_(fps))
        result = await self.db.execute(query)
        return set(result.scalars().all())

    async def create_many(self, transactions: list[StagedTransaction]) -> list[StagedTransaction]:
        if not transactions:
            return []
        self.db.add_all(transactions)
        await self.db.commit()
        for tx in transactions:
            await self.db.refresh(tx)
        return transactions

    async def save_all(self, transactions: list[StagedTransaction]) -> list[StagedTransaction]:
        return await self.create_many(transactions)

    async def save(self, tx: StagedTransaction) -> StagedTransaction:
        self.db.add(tx)
        await self.db.commit()
        await self.db.refresh(tx)
        return tx

    async def find_possible_duplicate_spent(
        self,
        account_id: UUID | None,
        amount: Decimal,
        tx_date: date,
        credit_card_id: UUID | None = None,
        tolerance_days: int = 3,
    ) -> Spent | None:
        start_d = tx_date - timedelta(days=tolerance_days)
        end_d = tx_date + timedelta(days=tolerance_days)
        amt_float = float(amount)
        low_amt = amt_float - 0.01
        high_amt = amt_float + 0.01

        query = select(Spent).where(
            func.date(Spent.created_at.op("AT TIME ZONE")("America/Sao_Paulo")) >= start_d,
            func.date(Spent.created_at.op("AT TIME ZONE")("America/Sao_Paulo")) <= end_d,
            Spent.amount >= low_amt,
            Spent.amount <= high_amt,
        )
        if credit_card_id:
            query = query.where(
                or_(Spent.credit_card_id == credit_card_id, Spent.credit_card_id.is_(None))
            )
        elif account_id:
            query = query.where(or_(Spent.account_id == account_id, Spent.account_id.is_(None)))
        result = await self.db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def find_possible_duplicate_income(
        self,
        account_id: UUID | None,
        amount: Decimal,
        tx_date: date,
        tolerance_days: int = 3,
    ) -> Income | None:
        start_d = tx_date - timedelta(days=tolerance_days)
        end_d = tx_date + timedelta(days=tolerance_days)
        amt_float = float(amount)
        low_amt = amt_float - 0.01
        high_amt = amt_float + 0.01

        query = select(Income).where(
            func.date(Income.received_at.op("AT TIME ZONE")("America/Sao_Paulo")) >= start_d,
            func.date(Income.received_at.op("AT TIME ZONE")("America/Sao_Paulo")) <= end_d,
            Income.amount >= low_amt,
            Income.amount <= high_amt,
        )
        if account_id:
            query = query.where(or_(Income.account_id == account_id, Income.account_id.is_(None)))
        result = await self.db.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def list_by_filter(
        self,
        batch_id: UUID | None = None,
        status: str | None = None,
        kind: str | None = None,
        only_duplicates: bool = False,
        only_unclassified: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> tuple[Sequence[StagedTransaction], int]:
        conditions = []
        if batch_id:
            conditions.append(StagedTransaction.batch_id == batch_id)
        if status:
            conditions.append(StagedTransaction.status == status)
        if kind:
            conditions.append(StagedTransaction.kind == kind)
        if only_duplicates:
            conditions.append(
                or_(
                    StagedTransaction.possible_duplicate_of_spent_id.is_not(None),
                    StagedTransaction.possible_duplicate_of_income_id.is_not(None),
                )
            )
        if only_unclassified:
            conditions.append(
                and_(
                    StagedTransaction.kind.in_(["EXPENSE", "INCOME"]),
                    StagedTransaction.category.is_(None),
                )
            )

        query = select(StagedTransaction)
        count_query = select(func.count(StagedTransaction.id))

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        offset = (page - 1) * size
        query = (
            query.order_by(
                StagedTransaction.occurred_at.desc(), StagedTransaction.created_at.desc()
            )
            .offset(offset)
            .limit(size)
        )

        total_res = await self.db.execute(count_query)
        total = total_res.scalar_one() or 0

        res = await self.db.execute(query)
        items = res.scalars().all()
        return items, total

    async def get_approved_for_commit(
        self, batch_id: UUID | None = None
    ) -> Sequence[StagedTransaction]:
        conditions = [StagedTransaction.status == "APPROVED"]
        if batch_id:
            conditions.append(StagedTransaction.batch_id == batch_id)
        query = (
            select(StagedTransaction)
            .where(and_(*conditions))
            .order_by(StagedTransaction.occurred_at.asc())
        )
        res = await self.db.execute(query)
        return res.scalars().all()

    async def list_for_reclassification(
        self, batch_id: UUID | None = None
    ) -> Sequence[StagedTransaction]:
        conditions = [
            StagedTransaction.status == "PENDING",
            StagedTransaction.kind.in_(["EXPENSE", "INCOME"]),
        ]
        if batch_id:
            conditions.append(StagedTransaction.batch_id == batch_id)
        query = select(StagedTransaction).where(and_(*conditions))
        res = await self.db.execute(query)
        return res.scalars().all()
