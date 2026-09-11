from typing import Any, Dict, List, Tuple
import uuid

from fastapi import HTTPException
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from agent_api.core.decorators import handle_service_errors
from agent_api.core.exceptions import (
    GraphServiceError,
    LLMParsingError,
    LLMProviderError,
    ServiceError,
)
from agent_api.core.logger import get_logger
from agent_api.repositories.chat_repository import ChatRepository
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.dtos import ChatMessage, ChatResponse
from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService
from agent_api.services.llm import get_llm_response

logger = get_logger(__name__)


class ChatService:
    def __init__(self, db_session: AsyncSession, http_client: httpx.AsyncClient):
        self.repository = ChatRepository(db_session)
        self.http_client = http_client
        self.finance_service = FinanceService(client=http_client)
        self.graph_service = GraphService(client=http_client)

    @handle_service_errors
    async def process_message(
        self, message: str, session_id_str: str | None, platform: str | None = None
    ) -> ChatResponse:
        logger.info(f"Processing message for session: {session_id_str}")

        # 1. Get or create session
        session_id = await self._get_or_create_session(session_id_str)

        # 2. Save user message
        await self._save_message(session_id, "user", message)

        # 3. Get chat history
        history_dicts, messages = await self._get_chat_history(session_id)

        # 4. Get initial LLM response
        response = await get_llm_response(history_dicts, platform)

        # 5. Handle textual balance query (without graph)
        if self._is_text_balance_query(response):
            response = await self._resolve_balance_query(response, history_dicts, platform)

        # 6. Handle graph generation
        image_base64, graph_context = None, None
        if response.requested_graph_type:
            image_base64, graph_context = await self._resolve_graph_query(response)

        # Save assistant message to history (enriched with graph context if present)
        history_content = (
            f"{response.response_message} {graph_context}".strip()
            if graph_context
            else response.response_message
        )
        await self._save_message(session_id, "assistant", history_content)

        # 7. Execute side-effect if action is confirmed (save spending/limit)
        await self._handle_finance_action(response)

        return self._build_response(
            session_id=session_id,
            response_text=response.response_message,
            previous_messages=messages,
            is_complete=response.is_complete,
            suggested_options=response.suggested_options,
            image_base64=image_base64,
        )

    def _is_text_balance_query(self, response: AssistantResponse) -> bool:
        return bool(response.is_balance_query and not response.requested_graph_type)

    async def _resolve_balance_query(
        self,
        response: AssistantResponse,
        history: List[Dict[str, Any]],
        platform: str | None,
    ) -> AssistantResponse:
        logger.info("Resolving balance query directly via Finance API")
        balances = await self.finance_service.get_balances()

        augmented_history = list(history)
        augmented_history.append(
            {
                "role": "user",
                "content": (
                    f"O sistema consultou a API financeira e retornou os seguintes dados de limites e gastos atuais:\n"
                    f"{balances}\n\n"
                    f"Por favor, formule a resposta final ao usuário de forma clara, educada e resumida."
                ),
            }
        )

        try:
            return await get_llm_response(augmented_history, platform)
        except (LLMProviderError, LLMParsingError, ServiceError) as e:
            logger.error(f"Failed to get LLM response with balance data: {e}")
            fallback_message = self._format_balance_fallback(balances)
            return AssistantResponse(
                response_message=fallback_message,
                is_balance_query=True,
                is_complete=True,
            )

    def _format_balance_fallback(self, balances: list[dict]) -> str:
        if not balances:
            return "Aqui estão seus limites e saldos disponíveis:\n(Nenhum limite encontrado)"
        lines = ["Aqui estão seus limites e saldos disponíveis:"]
        for item in balances:
            cat = item.get("category_display_name", item.get("category", ""))
            disp = item.get("available", item.get("disponivel", 0))
            lines.append(f"- {cat}: R$ {disp:.2f} disponíveis")
        return "\n".join(lines)

    async def _resolve_graph_query(
        self, response: AssistantResponse
    ) -> Tuple[str | None, str | None]:
        cats = response.requested_graph_categories
        mode = "saldo"
        balances = await self.finance_service.get_balances(categories=cats)

        if not balances:
            response.response_message = (
                "Não encontrei limites cadastrados ou gastos para as categorias solicitadas."
            )
            response.is_complete = False
            response.is_confirmed = False
            return None, "[Falha ao gerar gráfico: Sem dados de saldo/limites]"

        try:
            image_base64 = await self.graph_service.generate_chart(
                chart_type=response.requested_graph_type,
                balances=balances,
                mode=mode,
            )
            graph_context = f"[Gráfico gerado: {response.requested_graph_type}"
            if cats:
                graph_context += f", categorias: {', '.join(cats)}"
            graph_context += f", modo: {mode}]"
            response.response_message = "Aqui está o gráfico que você pediu!"
            response.is_complete = False
            response.is_confirmed = False
            return image_base64, graph_context
        except GraphServiceError as e:
            logger.error(f"Error generating graph: {e}")
            response.response_message = "Desculpe, ocorreu um erro ao gerar o gráfico."
            response.is_complete = False
            response.is_confirmed = False
            return None, None

    async def _get_or_create_session(self, session_id_str: str | None) -> uuid.UUID:
        if session_id_str:
            try:
                session_id = uuid.UUID(session_id_str)
            except ValueError:
                logger.warning(f"Invalid session_id format: {session_id_str}, creating new one.")
            else:
                session = await self.repository.get_session(session_id)
                if session:
                    return session.id
                logger.info(f"Session {session_id} not found, creating new one.")
        session = await self.repository.create_session()
        return session.id

    async def _save_message(self, session_id: uuid.UUID, role: str, content: str) -> None:
        await self.repository.add_message(session_id, role, content)

    async def _get_chat_history(
        self, session_id: uuid.UUID
    ) -> Tuple[List[Dict[str, Any]], List[ChatMessage]]:
        messages = await self.repository.get_messages(session_id)
        history_dicts = [{"role": m.role, "content": m.content} for m in reversed(messages)]
        return history_dicts, messages

    async def _handle_finance_action(self, response: AssistantResponse) -> None:
        if response.is_complete and response.is_confirmed:
            await self.finance_service.register(response)

    def _build_response(
        self,
        session_id: uuid.UUID,
        response_text: str,
        previous_messages: list[ChatMessage],
        is_complete: bool = False,
        suggested_options: list[str] | None = None,
        image_base64: str | None = None,
    ) -> ChatResponse:
        updated_history_dtos = [
            ChatMessage(role=m.role, content=m.content) for m in previous_messages
        ]
        updated_history_dtos.append(ChatMessage(role="assistant", content=response_text))

        return ChatResponse(
            response=response_text,
            session_id=str(session_id),
            history=updated_history_dtos,
            is_complete=is_complete,
            suggested_options=suggested_options,
            image_base64=image_base64,
        )
