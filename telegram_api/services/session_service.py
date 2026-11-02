"""Session management service for Telegram chats."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from telegram_api.core.database import get_db
from telegram_api.core.logger import get_logger
from telegram_api.repositories.session_repository import (
    SessionRepository,
    SessionRepositoryProtocol,
)
from telegram_api.settings import settings

logger = get_logger(__name__)


class SessionService:
    """Service to handle conversation sessions between Telegram chats and Agent API."""

    def __init__(self, repository: SessionRepositoryProtocol | None = None) -> None:
        self._repository = repository

    @asynccontextmanager
    async def _repository_scope(self) -> AsyncIterator[SessionRepositoryProtocol]:
        """Yields the injected repository or a short-lived one backed by the default DB."""
        if self._repository is not None:
            yield self._repository
            return

        async with get_db() as session:
            yield SessionRepository(session)

    async def get_active_session(
        self,
        chat_id: int,
        ttl_minutes: int | None = None,
    ) -> str | None:
        resolved_ttl = settings.SESSION_TTL_MINUTES if ttl_minutes is None else ttl_minutes
        async with self._repository_scope() as repo:
            return await repo.get_session(chat_id, ttl_minutes=resolved_ttl)

    async def sync_chat_session(
        self,
        chat_id: int,
        response_data: dict[str, Any],
    ) -> None:
        is_complete = response_data.get("is_complete", False)
        new_session_id = response_data.get("session_id")
        async with self._repository_scope() as repo:
            await self._apply_sync(repo, chat_id, is_complete, new_session_id)

    async def _apply_sync(
        self,
        repo: SessionRepositoryProtocol,
        chat_id: int,
        is_complete: bool,
        new_session_id: str | None,
    ) -> None:
        """Clears the session on completion or persists the new session id."""
        if is_complete:
            await repo.delete_session(chat_id)
            logger.info(f"Session cleared for chat {chat_id} (task complete)")
            return

        if new_session_id:
            await repo.save_session(chat_id, new_session_id)

    async def list_known_chat_ids(self) -> list[int]:
        async with self._repository_scope() as repo:
            return await repo.list_distinct_chat_ids()

    @staticmethod
    async def get_session(chat_id: int, ttl_minutes: int | None = None) -> str | None:
        """Get the active session ID for a chat if one exists and has not expired."""
        return await SessionService().get_active_session(chat_id, ttl_minutes=ttl_minutes)

    @staticmethod
    async def sync_session(chat_id: int, response_data: dict[str, Any]) -> None:
        """Synchronize the session state based on the agent's response."""
        await SessionService().sync_chat_session(chat_id, response_data)
