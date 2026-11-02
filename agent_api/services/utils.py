"""Pure helpers shared by the agent services."""

from collections.abc import Iterable

from agent_api.schemas.assistant import AssistantResponse


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
