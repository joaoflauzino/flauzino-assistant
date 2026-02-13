import uuid
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from telegram_api.models.session import TelegramSession
from telegram_api.core.logger import get_logger

logger = get_logger(__name__)


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_session(self, chat_id: int) -> Optional[str]:
        """Retrieve the session ID for a given chat ID."""
        try:
            query = select(TelegramSession.session_id).where(
                TelegramSession.chat_id == chat_id
            )
            result = await self.session.execute(query)
            session_id = result.scalar_one_or_none()

            if session_id:
                return str(session_id)
            return None
        except Exception as e:
            logger.error(f"Error retrieving session for chat_id {chat_id}: {e}")
            return None

    async def save_session(self, chat_id: int, session_id: str) -> None:
        """Save or update the session ID for a given chat ID."""
        try:
            # Upsert logic common in Postgres
            stmt = (
                insert(TelegramSession)
                .values(chat_id=chat_id, session_id=uuid.UUID(session_id))
                .on_conflict_do_update(
                    index_elements=[TelegramSession.chat_id],
                    set_=dict(
                        session_id=uuid.UUID(session_id),
                        updated_at=TelegramSession.updated_at.default.arg,  # Re-trigger default or just now()
                    ),
                )
            )
            # Note: SQLAlchemy's defaults might not trigger on upsert automatically depending on setup.
            # A cleaner way using explicit values:
            from datetime import datetime

            stmt = (
                insert(TelegramSession)
                .values(
                    chat_id=chat_id,
                    session_id=uuid.UUID(session_id),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                .on_conflict_do_update(
                    index_elements=[TelegramSession.chat_id],
                    set_=dict(
                        session_id=uuid.UUID(session_id), updated_at=datetime.utcnow()
                    ),
                )
            )

            await self.session.execute(stmt)
            await self.session.commit()
            logger.debug(f"Saved session {session_id} for chat_id {chat_id}")
        except Exception as e:
            logger.error(f"Error saving session for chat_id {chat_id}: {e}")
            await self.session.rollback()

    async def delete_session(self, chat_id: int) -> None:
        """Delete the session for a given chat ID."""
        try:
            stmt = delete(TelegramSession).where(TelegramSession.chat_id == chat_id)
            await self.session.execute(stmt)
            await self.session.commit()
            logger.debug(f"Deleted session for chat_id {chat_id}")
        except Exception as e:
            logger.error(f"Error deleting session for chat_id {chat_id}: {e}")
            await self.session.rollback()
