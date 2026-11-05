"""Schemas for receipt analysis returned by the OCR use case."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReceiptAnalysis:
    """Text and confidence obtained from a receipt image."""

    text: str
    confidence: float
