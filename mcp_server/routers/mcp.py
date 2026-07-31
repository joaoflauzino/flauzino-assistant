from fastapi import APIRouter
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.responses import Response

from core.mcp import mcp_server

router = APIRouter(tags=["mcp"])

sse_transport = SseServerTransport("/messages/")


@router.get("/sse")
async def handle_sse(request: Request) -> Response:
    """SSE endpoint for MCP protocol communication."""
    async with sse_transport.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())
    return Response()


def get_sse_transport() -> SseServerTransport:
    """Returns the SSE transport instance for mounting in the FastAPI app."""
    return sse_transport
