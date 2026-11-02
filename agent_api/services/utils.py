"""Pure helpers shared by the agent services."""

from agent_api.schemas.assistant import AssistantResponse


def attach_image(
    response: AssistantResponse,
    image_base64: str | None,
) -> AssistantResponse:
    """Attaches the agent state image to a response that does not carry one yet."""
    if image_base64 and not response.image_base64:
        response.image_base64 = image_base64
    return response
