"""Repository contracts for agent_api persistence.

This module declares only structural contracts (Protocols). The concrete
SQLAlchemy implementation lives in ``chat_repository.py`` and satisfies the
contract structurally, without inheriting from it.
"""

import uuid
from collections.abc import Sequence
from typing import Protocol

from agent_api.models.chat import ChatMessage, ChatSession


class ChatRepositoryProtocol(Protocol):
    """Domain repository contract for ChatSession and ChatMessage persistence."""

    async def create_session(self) -> ChatSession: ...

    async def get_session(self, session_id: uuid.UUID) -> ChatSession | None: ...

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
    ) -> ChatMessage: ...

    async def get_messages(
        self,
        session_id: uuid.UUID,
        limit: int = 10,
    ) -> Sequence[ChatMessage]: ...

    async def cleanup_stale_sessions(self, max_age_minutes: int = 30) -> int: ...
