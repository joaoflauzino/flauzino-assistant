"""Structural contracts for the transaction classification domain."""

from collections.abc import Callable
from typing import Protocol

from finance_api.schemas.classification import (
    ClassificationContext,
    ClassificationResult,
    ExtractedMerchantInfo,
    RawTransactionText,
)

type MerchantExtractorStep = Callable[[RawTransactionText], ExtractedMerchantInfo | None]
type MerchantExtractorPipeline = Callable[[RawTransactionText], ExtractedMerchantInfo]


class ClassificationHandlerProtocol(Protocol):
    """Structural contract for handlers in the transaction classification chain."""

    def set_next(
        self,
        handler: "ClassificationHandlerProtocol",
    ) -> "ClassificationHandlerProtocol": ...

    async def handle(self, ctx: ClassificationContext) -> ClassificationResult: ...
