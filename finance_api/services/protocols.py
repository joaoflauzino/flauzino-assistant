"""Protocols, Abstract Base Classes, and type contracts for finance_api services."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Protocol

from finance_api.models.categories import Category
from finance_api.models.income_categories import IncomeCategory
from finance_api.models.staged_transactions import StagedTransaction
from finance_api.schemas.classification import (
    ClassificationContext,
    ClassificationResult,
    ExtractedMerchantInfo,
    RawTransactionText,
)
from finance_api.schemas.imports import (
    BulkActionRequest,
    CommitContext,
    CommitStepOutcome,
    StepOutcome,
)

type MerchantExtractorStep = Callable[[RawTransactionText], ExtractedMerchantInfo | None]
type MerchantExtractorPipeline = Callable[[RawTransactionText], ExtractedMerchantInfo]


class CategoryLookupProtocol(Protocol):
    """Structural contract for looking up expense categories by key."""

    async def get_by_key(self, key: str) -> Category | None: ...


class IncomeCategoryLookupProtocol(Protocol):
    """Structural contract for looking up income categories by key."""

    async def get_by_key(self, key: str) -> IncomeCategory | None: ...


class BulkActionStrategy(Protocol):
    """Structural contract for executing a bulk action on a StagedTransaction."""

    async def execute(
        self,
        tx: StagedTransaction,
        req: BulkActionRequest,
    ) -> StepOutcome: ...


class TransactionCommitStrategy(Protocol):
    """Structural contract for committing an approved StagedTransaction."""

    async def commit(
        self,
        tx: StagedTransaction,
        ctx: CommitContext,
    ) -> CommitStepOutcome: ...


class ClassificationHandlerProtocol(Protocol):
    """Structural contract for handlers in the transaction classification chain."""

    def set_next(
        self,
        handler: "ClassificationHandlerProtocol",
    ) -> "ClassificationHandlerProtocol": ...

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult: ...


class BaseClassificationHandler(ABC):
    """Abstract base class providing fluent chaining and default fallback."""

    def __init__(self) -> None:
        self._next_handler: ClassificationHandlerProtocol | None = None

    def set_next(
        self,
        handler: ClassificationHandlerProtocol,
    ) -> ClassificationHandlerProtocol:
        self._next_handler = handler
        return handler

    @abstractmethod
    async def handle(self, ctx: ClassificationContext) -> ClassificationResult:
        if self._next_handler is not None:
            return await self._next_handler.handle(ctx)
        # Fallback final se nenhum handler classificar a categoria (aguarda IA em lote)
        return ClassificationResult(
            merchant=ctx.merchant,
            kind=ctx.default_kind,
            payment_type=ctx.default_payment_type,
            suggested_category=None,
            suggestion_source=None,
            confidence=None,
            description=ctx.description,
            location=ctx.location,
        )
