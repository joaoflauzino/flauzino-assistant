from typing import Sequence
import unicodedata
from uuid import UUID

from sqlalchemy import delete, desc, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.models.category_rules import CategoryRule


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper().strip()


class CategoryRuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> Sequence[CategoryRule]:
        result = await self.db.execute(
            select(CategoryRule).order_by(desc(CategoryRule.hits), CategoryRule.pattern.asc())
        )
        return result.scalars().all()

    async def find_matching_rule(self, merchant: str, direction: str) -> CategoryRule | None:
        norm_merchant = _normalize(merchant)
        rules = await self.list_all()
        for rule in rules:
            if rule.direction != direction:
                continue
            norm_pattern = _normalize(rule.pattern)
            if rule.match_type == "EXACT":
                if norm_merchant == norm_pattern:
                    return rule
            else:  # CONTAINS
                if norm_pattern in norm_merchant:
                    return rule
        return None

    async def increment_hits(self, rule_id: UUID) -> None:
        await self.db.execute(
            update(CategoryRule)
            .where(CategoryRule.id == rule_id)
            .values(hits=CategoryRule.hits + 1)
        )
        await self.db.commit()

    async def upsert_rule(
        self,
        pattern: str,
        direction: str,
        kind: str,
        category: str | None,
        source: str = "LEARNED",
    ) -> CategoryRule:
        cleaned_pattern = pattern.strip()
        stmt = (
            pg_insert(CategoryRule)
            .values(
                pattern=cleaned_pattern,
                match_type="CONTAINS",
                direction=direction,
                kind=kind,
                category=category,
                hits=1,
                source=source,
            )
            .on_conflict_do_update(
                constraint="uq_category_rules_pattern_direction",
                set_={
                    "category": category,
                    "kind": kind,
                    "hits": CategoryRule.hits + 1,
                    "source": source,
                },
            )
            .returning(CategoryRule)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one()

    async def delete_by_id(self, rule_id: UUID) -> bool:
        stmt = delete(CategoryRule).where(CategoryRule.id == rule_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
