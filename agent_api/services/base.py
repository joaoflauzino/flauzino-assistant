"""Base HTTP Service for services consuming external APIs."""

import httpx


class BaseHttpService:
    """Base service class requiring an explicit HTTP client."""

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
