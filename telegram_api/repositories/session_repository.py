import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from telegram_api.core.logger import get_logger
from telegram_api.models.session import TelegramSession

logger = get_logger(__name__)


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_session(self, chat_id: int, ttl_minutes: int | None = None) -> Optional[str]:
        """Retrieve the session ID for a given chat ID if not expired."""
        try:
            query = select(TelegramSession).where(TelegramSession.chat_id == chat_id)
            result = await self.session.execute(query)
            session_record = result.scalar_one_or_none()

            if not session_record:
                return None

            if ttl_minutes is not None and ttl_minutes > 0:
                now = datetime.now(timezone.utc)
                updated_at = session_record.updated_at
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)

                if now - updated_at > timedelta(minutes=ttl_minutes):
                    logger.info(
                        f"Session {session_record.session_id} for chat_id {chat_id} "
                        f"expired (inactive for > {ttl_minutes}m). Clearing session."
                    )
                    await self.session.delete(session_record)
                    await self.session.commit()
                    return None

            return str(session_record.session_id)
        except Exception as e:
            logger.error(f"Error retrieving session for chat_id {chat_id}: {e}")
            return None

    async def save_session(self, chat_id: int, session_id: str) -> None:
        """Save or update the session ID for a given chat ID."""
        try:
            now = datetime.now(timezone.utc)
            stmt = (
                insert(TelegramSession)
                .values(
                    chat_id=chat_id,
                    session_id=uuid.UUID(session_id),
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[TelegramSession.chat_id],
                    set_=dict(session_id=uuid.UUID(session_id), updated_at=now),
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
