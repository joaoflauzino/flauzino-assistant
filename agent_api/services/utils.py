"""Pure helpers shared by the agent services."""

from collections.abc import Iterable

from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.classify import ClassifyItemInput

DEFAULT_CONFIDENCE = 0.75


def attach_image(
    response: AssistantResponse,
    image_base64: str | None,
) -> AssistantResponse:
    """Attaches the agent state image to a response that does not carry one yet."""
    if image_base64 and not response.image_base64:
        response.image_base64 = image_base64
    return response


def clean_extracted_text(text: str) -> str:
    """Strips the surrounding whitespace Tesseract adds around recognised text."""
    return text.strip()


def average_confidence(values: Iterable[str]) -> float:
    """Averages Tesseract confidence values, ignoring the ``-1`` sentinel for empty regions."""
    confidences = [float(value) for value in values if value != "-1"]
    if not confidences:
        return 0.0
    return sum(confidences) / len(confidences)


def build_tx_payload(transactions: list[ClassifyItemInput]) -> list[dict[str, object]]:
    """Serialises the transactions into the minimal JSON payload sent to the LLM."""
    return [
        {
            "id": transaction.id,
            "merchant": transaction.merchant,
            "raw_title": transaction.raw_title,
            "raw_description": transaction.raw_description,
            "direction": transaction.direction,
            "amount": transaction.amount,
        }
        for transaction in transactions
    ]


def normalize_confidence(confidence: float | None) -> float:
    """Rounds the LLM confidence, falling back to the default when it is missing."""
    if confidence is None:
        return DEFAULT_CONFIDENCE
    return round(float(confidence), 2)


def quote_join(values: list[str]) -> str:
    """Joins values as a comma-separated list of single-quoted strings."""
    return ", ".join(f"'{value}'" for value in values)
