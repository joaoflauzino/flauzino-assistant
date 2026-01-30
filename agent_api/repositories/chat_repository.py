import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_api.models.chat import ChatMessage, ChatSession


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self) -> ChatSession:
        chat_session = ChatSession()
        self.session.add(chat_session)
        await self.session.commit()
        await self.session.refresh(chat_session)
        return chat_session

    async def get_session(self, session_id: uuid.UUID) -> ChatSession | None:
        query = (
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add_message(
        self, session_id: uuid.UUID, role: str, content: str
    ) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_messages(
        self, session_id: uuid.UUID, limit: int = 5
    ) -> List[ChatMessage]:
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        messages = result.scalars().all()

        return messages
