"""Unit tests for the pure helpers shared by the agent services."""

from agent_api.schemas.assistant import AssistantResponse
from agent_api.services.utils import attach_image, average_confidence, clean_extracted_text


def _response(image_base64: str | None = None) -> AssistantResponse:
    return AssistantResponse(
        response_message="Mensagem de teste",
        suggested_options=["Sim", "Não"],
        is_complete=True,
        image_base64=image_base64,
    )


def test_attach_image_attaches_state_image_when_response_has_none():
    """The agent state image is attached to a response that does not carry one yet."""
    response = _response()

    result = attach_image(response, "base64_chart_bytes")

    assert result.image_base64 == "base64_chart_bytes"
    assert result is response


def test_attach_image_preserves_existing_response_image():
    """A response that already carries an image must not be overridden by the state."""
    response = _response(image_base64="image_from_response")

    result = attach_image(response, "image_from_state")

    assert result.image_base64 == "image_from_response"


def test_attach_image_noop_when_state_image_is_none():
    """A missing state image leaves a response without an image untouched."""
    response = _response()

    result = attach_image(response, None)

    assert result.image_base64 is None


def test_attach_image_noop_when_both_images_are_set():
    """When both images exist, the response image wins and nothing changes."""
    response = _response(image_base64="image_from_response")

    result = attach_image(response, "image_from_state")

    assert result.image_base64 == "image_from_response"
    assert result.response_message == "Mensagem de teste"
    assert result.suggested_options == ["Sim", "Não"]
    assert result.is_complete is True


def test_clean_extracted_text_strips_surrounding_whitespace():
    """Tesseract output is trimmed before being returned to callers."""
    assert clean_extracted_text("  \n  Text with spaces  \n  ") == "Text with spaces"


def test_clean_extracted_text_keeps_blank_output_blank():
    """Whitespace-only output becomes an empty string, which triggers the empty-text guard."""
    assert clean_extracted_text("   ") == ""


def test_average_confidence_ignores_the_minus_one_sentinel():
    """Confidence values of -1 mark empty regions and must not drag the average down."""
    assert average_confidence(["80", "-1", "60"]) == 70.0


def test_average_confidence_returns_zero_when_no_values_are_usable():
    """A result set without usable confidences yields 0.0 instead of a division error."""
    assert average_confidence([]) == 0.0
    assert average_confidence(["-1", "-1"]) == 0.0
