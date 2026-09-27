"""Session management service for Telegram chats."""

from typing import Any

from telegram_api.core.database import get_db
from telegram_api.core.logger import get_logger
from telegram_api.repositories.session_repository import SessionRepository
from telegram_api.settings import settings

logger = get_logger(__name__)


class SessionService:
    """Service to handle conversation sessions between Telegram chats and Agent API."""

    @staticmethod
    async def get_session(chat_id: int, ttl_minutes: int | None = None) -> str | None:
        """Get the active session ID for a chat if one exists and has not expired."""
        if ttl_minutes is None:
            ttl_minutes = settings.SESSION_TTL_MINUTES

        async with get_db() as session:
            repo = SessionRepository(session)
            return await repo.get_session(chat_id, ttl_minutes=ttl_minutes)

    @staticmethod
    async def sync_session(chat_id: int, response_data: dict[str, Any]) -> None:
        """Synchronize the session state based on the agent's response.

        If the conversation task is marked complete (is_complete=True), the active session is deleted.
        Otherwise, if a new session_id is returned by the agent, it is saved for future interactions.
        """
        is_complete = response_data.get("is_complete", False)
        async with get_db() as session:
            repo = SessionRepository(session)
            if is_complete:
                await repo.delete_session(chat_id)
                logger.info(f"Session cleared for chat {chat_id} (task complete)")
            else:
                new_session_id = response_data.get("session_id")
                if new_session_id:
                    await repo.save_session(chat_id, new_session_id)
