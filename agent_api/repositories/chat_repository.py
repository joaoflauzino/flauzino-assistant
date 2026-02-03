import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_api.models.chat import ChatMessage, ChatSession
from agent_api.core.logger import get_logger

logger = get_logger(__name__)


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self) -> ChatSession:
        chat_session = ChatSession()
        self.session.add(chat_session)
        await self.session.commit()
        await self.session.refresh(chat_session)
        logger.info(f"Session created: {chat_session.id}")
        return chat_session

    async def get_session(self, session_id: uuid.UUID) -> ChatSession | None:
        query = (
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )
        result = await self.session.execute(query)
        session = result.scalar_one_or_none()
        if session:
            logger.info(f"Retrieved session: {session.id}")
        return session

    async def add_message(
        self, session_id: uuid.UUID, role: str, content: str
    ) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        logger.info(f"Message added to session {session_id} by {role}")
        return message

    async def get_messages(
        self, session_id: uuid.UUID, limit: int = 10
    ) -> List[ChatMessage]:
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        messages = result.scalars().all()
        logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
        return messages
