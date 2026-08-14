import uuid
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from typing import List, Dict, Any, Tuple

from agent_api.core.decorators import handle_service_errors
from agent_api.repositories.chat_repository import ChatRepository
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.dtos import ChatMessage, ChatResponse
from agent_api.services import mcp_client
from agent_api.services.finance import FinanceService
from agent_api.services.llm import get_llm_response
from agent_api.core.logger import get_logger
from agent_api.settings import settings

logger = get_logger(__name__)


class ChatService:
    def __init__(self, db_session: AsyncSession, http_client: httpx.AsyncClient):
        self.repository = ChatRepository(db_session)
        self.http_client = http_client

    @handle_service_errors
    async def process_message(
        self, message: str, session_id_str: str | None, platform: str | None = None
    ) -> ChatResponse:
        logger.info(f"Processing message for session: {session_id_str}")
        session_id = await self._get_or_create_session(session_id_str)

        await self._save_message(session_id, "user", message)

        history_dicts, messages = await self._get_chat_history(session_id)

        response = await get_llm_response(history_dicts, platform)

        # Intercept balance query for text response
        if getattr(response, "is_balance_query", False) and not getattr(
            response, "requested_graph_type", None
        ):
            url = f"{settings.FINANCE_SERVICE_URL}/limits/balance"
            api_resp = await self.http_client.get(url)
            balances = api_resp.json() if api_resp.status_code == 200 else []

            # Feed the data back to the LLM to formulate a natural response
            sys_msg = f"DADOS DO SISTEMA (Saldos Atuais): {balances}. Ação Obrigatória: Usando apenas os dados fornecidos, escreva a resposta final para o usuário agora mesmo. NÃO diga frases como 'Vou verificar', 'Um momento', etc. Dê a resposta direta com os valores. Se não houver limites ou saldo na categoria pedida, avise o usuário explicitamente."
            history_dicts.append({"role": "system", "content": sys_msg})

            try:
                response = await get_llm_response(history_dicts, platform)
            except Exception as e:
                logger.error(f"Error on second LLM call for balance query: {e}")
                fallback_msg = "Aqui estão os seus saldos (resposta direta do sistema devido a uma lentidão na IA):\n"
                if not balances:
                    fallback_msg = "Não há limites cadastrados ou dados suficientes para calcular o saldo atual."
                else:
                    for b in balances:
                        fallback_msg += f"- {b.get('category_display_name', 'Categoria')}: Limite R$ {b.get('limit', 0):.2f} / Restante R$ {b.get('available', 0):.2f}\n"
                response.response_message = fallback_msg

            response.is_complete = True
            response.is_confirmed = True

        # Handle MCP Graph Generation
        image_base64 = None
        graph_context = None
        if getattr(response, "requested_graph_type", None):
            logger.info(f"LLM requested graph via MCP: {response.requested_graph_type}")
            try:
                arguments = {}
                if getattr(response, "requested_graph_categories", None):
                    arguments["categories"] = response.requested_graph_categories
                if getattr(response, "requested_graph_mode", None):
                    arguments["mode"] = response.requested_graph_mode

                result = await mcp_client.call_tool(response.requested_graph_type, arguments)

                # Extract the base64 image or text from the MCP response
                if result.image_base64:
                    image_base64 = result.image_base64
                    mcp_text_response = None
                else:
                    mcp_text_response = result.text

                if image_base64:
                    graph_context = f"[Gráfico gerado: {response.requested_graph_type}"
                    if getattr(response, "requested_graph_categories", None):
                        graph_context += (
                            f", categorias: {', '.join(response.requested_graph_categories)}"
                        )
                    if getattr(response, "requested_graph_mode", None):
                        graph_context += f", modo: {response.requested_graph_mode}"
                    graph_context += "]"
                    response.response_message = "Aqui está o gráfico que você pediu!"
                elif mcp_text_response:
                    response.response_message = mcp_text_response
                    graph_context = f"[Falha ao gerar gráfico: {mcp_text_response}]"
                else:
                    response.response_message = "Desculpe, não foi possível gerar o gráfico."
                    graph_context = "[Falha ao gerar gráfico: Resposta vazia do MCP]"

                response.is_complete = False
                response.is_confirmed = False
            except Exception as e:
                logger.error(f"Error calling MCP server: {e}")
                response.response_message = "Desculpe, ocorreu um erro ao gerar o gráfico."
                graph_context = None

        # Save history message: enrich with graph context for LLM follow-ups
        history_message = response.response_message
        if graph_context:
            history_message = f"{response.response_message} {graph_context}"
        await self._save_message(session_id, "assistant", history_message)

        await self._handle_finance_action(response)

        # Determine completion status.
        # We consider the session "complete" (ready to be cleared) if the assistant
        # has successfully performed a confirmed action (is_complete and is_confirmed).
        # Or if the user explicitly cancels/completes a flow (logic could be expanded).
        # For now, let's use the flags from AssistantResponse.
        is_flow_complete = response.is_complete and response.is_confirmed

        return self._build_response(
            session_id,
            response.response_message,
            messages,
            is_flow_complete,
            response.suggested_options,
            image_base64,
        )

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
                else:
                    logger.warning(f"Session {session_id} not found, creating new one.")

        session = await self.repository.create_session()
        logger.info(f"Created new session: {session.id}")
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
            finance_service = FinanceService(response, self.http_client)
            await finance_service.register()

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
