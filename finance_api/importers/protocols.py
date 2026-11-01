from typing import Protocol
from uuid import UUID

from finance_api.importers.schemas import (
    ParsedStatement,
    ResolvedImportTarget,
    StatementType,
)


class StatementParser(Protocol):
    name: str
    statement_type: StatementType

    def can_parse(self, content: bytes, filename: str) -> bool: ...

    def parse(self, content: bytes, filename: str) -> ParsedStatement: ...


class ImportTargetResolver(Protocol):
    async def resolve(
        self,
        account_id: UUID | None,
        credit_card_id: UUID | None,
        bank_hint: str | None = None,
    ) -> ResolvedImportTarget: ...
