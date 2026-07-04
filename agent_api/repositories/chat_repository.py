import uuid
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import delete, func, select
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

    async def add_message(self, session_id: uuid.UUID, role: str, content: str) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        logger.info(f"Message added to session {session_id} by {role}")
        return message

    async def get_messages(self, session_id: uuid.UUID, limit: int = 10) -> List[ChatMessage]:
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

    async def cleanup_stale_sessions(self, max_age_minutes: int = 30) -> int:
        """Delete sessions with no messages in the last `max_age_minutes` minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)

        # Find sessions whose last message is older than cutoff
        subquery = (
            select(
                ChatMessage.session_id,
                func.max(ChatMessage.created_at).label("last_msg"),
            )
            .group_by(ChatMessage.session_id)
            .subquery()
        )
        stale_ids = select(subquery.c.session_id).where(subquery.c.last_msg < cutoff)

        result = await self.session.execute(
            delete(ChatSession).where(ChatSession.id.in_(stale_ids))
        )
        await self.session.commit()
        deleted_count = result.rowcount
        if deleted_count:
            logger.info(f"Cleaned up {deleted_count} stale chat sessions")
        return deleted_count
