"""HTTP contract required by the AI classification client."""

from typing import Any, Protocol

import httpx


class AIClassifierHttpClientProtocol(Protocol):
    """HTTP contract required by the AI classification client."""

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        timeout: float,
    ) -> httpx.Response: ...
