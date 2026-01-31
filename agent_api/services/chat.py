import uuid
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from typing import List, Dict, Any, Tuple

from agent_api.core.decorators import handle_chat_service_errors
from agent_api.repositories.chat_repository import ChatRepository
from agent_api.schemas.assistant import AssistantResponse
from agent_api.schemas.dtos import ChatMessage, ChatResponse
from agent_api.services.finance import FinanceService
from agent_api.services.llm import get_llm_response


class ChatService:
    def __init__(self, db_session: AsyncSession, http_client: httpx.AsyncClient):
        self.repository = ChatRepository(db_session)
        self.http_client = http_client

    @handle_chat_service_errors
    async def process_message(
        self, message: str, session_id_str: str | None
    ) -> ChatResponse:
        session_id = await self._get_or_create_session(session_id_str)

        await self._save_message(session_id, "user", message)

        history_dicts, messages = await self._get_chat_history(session_id)

        response = await get_llm_response(history_dicts)

        await self._save_message(session_id, "assistant", response.response_message)

        await self._handle_finance_action(response)

        return self._build_response(session_id, response.response_message, messages)

    async def _get_or_create_session(self, session_id_str: str | None) -> uuid.UUID:
        if session_id_str:
            try:
                session_id = uuid.UUID(session_id_str)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid session_id format")

            session = await self.repository.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            return session.id
        else:
            session = await self.repository.create_session()
            return session.id

    async def _save_message(
        self, session_id: uuid.UUID, role: str, content: str
    ) -> None:
        await self.repository.add_message(session_id, role, content)

    async def _get_chat_history(
        self, session_id: uuid.UUID
    ) -> Tuple[List[Dict[str, Any]], List[ChatMessage]]:
        messages = await self.repository.get_messages(session_id)
        history_dicts = [
            {"role": m.role, "content": m.content} for m in reversed(messages)
        ]
        return history_dicts, messages

    async def _handle_finance_action(self, response: AssistantResponse) -> None:
        if response.is_complete:
            finance_service = FinanceService(response, self.http_client)
            await finance_service.register()

    def _build_response(
        self,
        session_id: uuid.UUID,
        response_text: str,
        previous_messages: list[ChatMessage],
    ) -> ChatResponse:
        updated_history_dtos = [
            ChatMessage(role=m.role, content=m.content) for m in previous_messages
        ]
        updated_history_dtos.append(
            ChatMessage(role="assistant", content=response_text)
        )

        return ChatResponse(
            response=response_text,
            session_id=str(session_id),
            history=updated_history_dtos,
        )
