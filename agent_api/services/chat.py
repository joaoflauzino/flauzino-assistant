from typing import Any, Dict, List, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from agent_api.core.decorators import handle_service_errors
from agent_api.core.logger import get_logger
from agent_api.repositories.chat_repository import ChatRepository
from agent_api.schemas.dtos import ChatMessage, ChatResponse
from agent_api.services.agent import AgentService

logger = get_logger(__name__)


class ChatService:
    def __init__(
        self,
        db_session: AsyncSession,
        agent_service: AgentService,
    ):
        self.repository = ChatRepository(db_session)
        self.agent_service = agent_service

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

        # 4. Get Agent LLM response
        response = await self.agent_service.get_response(
            history_dicts,
            platform=platform,
        )

        # 5. Save assistant message to history
        await self._save_message(session_id, "assistant", response.response_message)

        # 6. Build and return API response
        return self._build_response(
            session_id=session_id,
            response_text=response.response_message,
            previous_messages=messages,
            is_complete=response.is_complete,
            suggested_options=response.suggested_options,
            image_base64=response.image_base64,
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
