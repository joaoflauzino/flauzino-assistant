from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from agent_api.schemas.assistant import AssistantResponse
from agent_api.services.agent import AgentService, AgentStateWithImage
from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService

__all__ = [
    "AgentService",
    "AgentStateWithImage",
    "get_llm_response",
    "get_system_prompt",
]


async def get_system_prompt(
    finance_service: FinanceService,
    platform: str | None = None,
) -> str:
    """Convenience helper for generating system prompt."""
    dummy_service = AgentService(
        llm=None,  # type: ignore
        finance_service=finance_service,
        graph_service=None,  # type: ignore
    )
    return await dummy_service.get_system_prompt(platform=platform)


async def get_llm_response(
    chat_history: list[dict[str, Any]],
    finance_service: FinanceService,
    graph_service: GraphService,
    llm: BaseChatModel,
    platform: str | None = None,
) -> AssistantResponse:
    """Convenience helper for running agent response."""
    agent_service = AgentService(
        llm=llm,
        finance_service=finance_service,
        graph_service=graph_service,
    )
    return await agent_service.get_response(chat_history, platform=platform)
