import httpx


class HTTPClientManager:
    def __init__(self):
        self.client: httpx.AsyncClient | None = None

    async def stop(self):
        if self.client:
            await self.client.aclose()
            self.client = None

    def get_client(self) -> httpx.AsyncClient:
        if not self.client:
            self.client = httpx.AsyncClient()
        return self.client


http_client_manager = HTTPClientManager()


def get_http_client() -> httpx.AsyncClient:
    return http_client_manager.get_client()
