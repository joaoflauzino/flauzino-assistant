from collections.abc import Sequence
from typing import Any, Protocol, cast
from uuid import UUID

from sqlalchemy import delete, desc, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from finance_api.core.text import normalize_upper
from finance_api.models.category_rules import CategoryRule


class CategoryRuleRepositoryProtocol(Protocol):
    """Domain repository contract for CategoryRule persistence."""

    async def list_all(self) -> Sequence[CategoryRule]: ...

    async def find_matching_rule(self, merchant: str, direction: str) -> CategoryRule | None: ...

    async def increment_hits(self, rule_id: UUID) -> None: ...

    async def upsert_rule(
        self,
        pattern: str,
        direction: str,
        kind: str,
        category: str | None,
        source: str = "LEARNED",
    ) -> CategoryRule: ...

    async def delete_by_id(self, rule_id: UUID) -> bool: ...


class CategoryRuleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self) -> Sequence[CategoryRule]:
        result = await self.db.execute(
            select(CategoryRule).order_by(desc(CategoryRule.hits), CategoryRule.pattern.asc())
        )
        return result.scalars().all()

    async def find_matching_rule(self, merchant: str, direction: str) -> CategoryRule | None:
        norm_merchant = normalize_upper(merchant)
        for rule in await self.list_all():
            if rule.direction != direction:
                continue
            if self._matches_rule(rule, norm_merchant):
                return rule
        return None

    def _matches_rule(self, rule: CategoryRule, norm_merchant: str) -> bool:
        """Tells whether the rule pattern matches the normalized merchant."""
        norm_pattern = normalize_upper(rule.pattern)
        if rule.match_type == "EXACT":
            return norm_merchant == norm_pattern
        return norm_pattern in norm_merchant

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
        result = cast(CursorResult[Any], await self.db.execute(stmt))
        await self.db.commit()
        return result.rowcount > 0
