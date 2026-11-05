import asyncio
from typing import Any, NotRequired, cast

from langchain.agents import AgentState, create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolCall

from agent_api.core.callbacks import AgentLoggingCallbackHandler
from agent_api.core.decorators import handle_llm_errors
from agent_api.core.logger import get_logger
from agent_api.schemas.assistant import AssistantResponse
from agent_api.services.protocols import FinanceServiceProtocol, GraphServiceProtocol
from agent_api.services.system_prompt import PromptMetadata, build_system_prompt
from agent_api.services.tools.registry import create_agent_tools
from agent_api.services.utils import attach_image

logger = get_logger(__name__)


class AgentStateWithCustom(AgentState):
    image_base64: NotRequired[str | None]
    final_response: NotRequired[dict[str, Any] | None]


class AgentService:
    """Encapsulates LangChain agent lifecycle, tool execution, and prompt generation."""

    def __init__(
        self,
        llm: BaseChatModel,
        finance_service: FinanceServiceProtocol,
        graph_service: GraphServiceProtocol,
    ) -> None:
        self.llm = llm
        self.finance_service = finance_service
        self.graph_service = graph_service
        self.tools = create_agent_tools(finance_service, graph_service)

    async def get_system_prompt(self, platform: str | None = None) -> str:
        """Dynamically generate system prompt with valid categories, accounts and cards."""
        metadata = await self._load_prompt_metadata()
        return build_system_prompt(metadata, platform)

    async def _load_prompt_metadata(self) -> PromptMetadata:
        """Fetches financial metadata, falling back to empty lists on failure."""
        try:
            (
                categories,
                income_categories,
                payment_methods,
                accounts,
                credit_cards,
            ) = await asyncio.gather(
                self.finance_service.get_categories(),
                self.finance_service.get_income_categories(),
                self.finance_service.get_payment_methods(),
                self.finance_service.get_accounts(),
                self.finance_service.get_credit_cards(),
            )
        except Exception as error:
            logger.warning(
                f"Failed to fetch dynamic financial metadata for system prompt: {error}. "
                "Falling back to empty lists."
            )
            return PromptMetadata.empty()
        return PromptMetadata.from_collections(
            categories,
            income_categories,
            payment_methods,
            accounts,
            credit_cards,
        )

    def _build_messages(self, chat_history: list[dict[str, Any]]) -> list[BaseMessage]:
        """Converts incoming chat history dictionaries into LangChain BaseMessage objects."""
        messages: list[BaseMessage] = []
        for msg in chat_history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))
        return messages

    def _extract_assistant_response(self, result: dict[str, Any]) -> AssistantResponse:
        """Extracts and normalizes AssistantResponse from LangChain result dictionary."""
        image_base64 = result.get("image_base64")
        extractors = (self._from_structured_state, self._from_tool_calls)

        for extract in extractors:
            response = extract(result)
            if response is not None:
                return attach_image(response, image_base64)

        return self._fallback_response(result)

    def _from_structured_state(self, result: dict[str, Any]) -> AssistantResponse | None:
        """Reads AssistantResponse from the root of the returned state."""
        structured_resp = result.get("structured_response")

        if isinstance(structured_resp, AssistantResponse):
            logger.info(
                f"🎯 [AGENT:EXTRACT] structured_response extraído diretamente do state: {structured_resp}"
            )
            return structured_resp

        if not isinstance(structured_resp, dict):
            return None

        response = AssistantResponse(**structured_resp)
        logger.info(f"🎯 [AGENT:EXTRACT] structured_response dict convertido: {response}")
        return response

    def _from_tool_calls(self, result: dict[str, Any]) -> AssistantResponse | None:
        """Resilience path: reads the AssistantResponse tool call from the messages."""
        for message in reversed(result.get("messages", [])):
            if not isinstance(message, AIMessage) or not message.tool_calls:
                continue

            response = self._response_from_tool_calls(message.tool_calls)
            if response is not None:
                return response

        return None

    def _response_from_tool_calls(self, tool_calls: list[ToolCall]) -> AssistantResponse | None:
        for tool_call in tool_calls:
            if tool_call.get("name") != "AssistantResponse":
                continue

            response = AssistantResponse(**(tool_call.get("args") or {}))
            logger.info(f"🎯 [AGENT:EXTRACT] Extraído de AIMessage.tool_calls: {response}")
            return response

        return None

    def _fallback_response(self, result: dict[str, Any]) -> AssistantResponse:
        """Fallback path: the model answered with plain text instead of a structure."""
        messages = result.get("messages", [])
        last_msg = messages[-1] if messages else None
        response_text = (
            str(last_msg.content)
            if last_msg and getattr(last_msg, "content", None)
            else "Desculpe, não consegui processar a resposta adequadamente."
        )
        logger.warning(
            f"⚠️ [AGENT:FALLBACK] Structured response não encontrada. Usando texto: {repr(response_text)[:100]}"
        )
        return AssistantResponse(
            response_message=response_text,
            is_complete=False,
            suggested_options=["Sim", "Não"],
            image_base64=result.get("image_base64"),
        )

    @handle_llm_errors
    async def get_response(
        self,
        chat_history: list[dict[str, Any]],
        platform: str | None = None,
    ) -> AssistantResponse:
        """Run agent with LangChain create_agent and extract response via ToolStrategy(AssistantResponse)."""
        system_prompt = await self.get_system_prompt(platform=platform)

        agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt,
            response_format=ToolStrategy(schema=AssistantResponse),
            state_schema=AgentStateWithCustom,
        )

        messages = self._build_messages(chat_history)
        callback_handler = AgentLoggingCallbackHandler()
        agent_input = cast(Any, {"messages": messages})
        result = await agent.ainvoke(
            agent_input,
            config={"callbacks": [callback_handler]},
        )

        # Logging detalhado do que o agent.ainvoke produziu
        msgs = result.get("messages", [])
        msgs_summary = [
            f"{type(m).__name__}(content={repr(m.content)[:80]}, tool_calls={getattr(m, 'tool_calls', None)})"
            for m in msgs
        ]
        logger.info(
            f"🔍 [AGENT:RESULT] keys={list(result.keys())} | structured_response={repr(result.get('structured_response'))} | messages={msgs_summary}"
        )

        return self._extract_assistant_response(result)
