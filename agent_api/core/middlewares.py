"""HTTP middlewares for agent_api."""

from collections.abc import Awaitable, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from agent_api.core.correlation import CORRELATION_HEADER, set_request_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts or generates a Correlation ID for each request."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming_id = request.headers.get(CORRELATION_HEADER)
        req_id = set_request_id(incoming_id)

        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = req_id
        return response
