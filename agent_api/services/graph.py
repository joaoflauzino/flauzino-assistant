import httpx

from agent_api.core.exceptions import GraphServiceError
from agent_api.core.logger import get_logger
from agent_api.services.base import BaseHttpService
from agent_api.settings import settings

logger = get_logger(__name__)


class GraphService(BaseHttpService):
    def __init__(self, client: httpx.AsyncClient):
        super().__init__(client)

    async def generate_chart(
        self,
        chart_type: str,
        balances: list[dict],
        mode: str = "saldo",
        title: str | None = None,
    ) -> str:
        """Calls the graph_api REST endpoint and returns base64 image."""
        endpoint = "pie" if "pie" in chart_type.lower() else "bar"
        url = f"{settings.GRAPH_SERVICE_URL.rstrip('/')}/graphs/{endpoint}"
        payload = {
            "balances": balances,
            "title": title,
        }
        if endpoint == "bar":
            payload["mode"] = mode

        logger.info(f"Requesting graph from {url} (type={chart_type}, mode={mode})")

        try:
            response = await self.client.post(url, json=payload, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            return data["image_base64"]
        except Exception as e:
            logger.error(f"Error calling graph service at {url}: {e}")
            raise GraphServiceError(f"Failed to generate graph: {e}")
