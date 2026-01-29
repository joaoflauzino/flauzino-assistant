from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI


class HTTPClientManager:
    def __init__(self):
        self.client: httpx.AsyncClient | None = None

    async def start(self):
        self.client = httpx.AsyncClient()

    async def stop(self):
        if self.client:
            await self.client.aclose()
            self.client = None

    def get_client(self) -> httpx.AsyncClient:
        if not self.client:
            raise RuntimeError("HTTP client is not initialized.")
        return self.client


http_client_manager = HTTPClientManager()


def get_http_client() -> httpx.AsyncClient:
    return http_client_manager.get_client()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await http_client_manager.start()
    yield
    await http_client_manager.stop()
