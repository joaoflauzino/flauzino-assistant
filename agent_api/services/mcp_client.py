from dataclasses import dataclass, field

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Tool

from agent_api.core.logger import get_logger
from agent_api.settings import settings

logger = get_logger(__name__)


@dataclass
class MCPServerResult:
    """Result of an MCP tool call."""

    image_base64: str | None = None
    text: str | None = None
    is_error: bool = False
    content: list = field(default_factory=list)


def _mcp_url() -> str:
    return f"{settings.MCP_SERVER_URL.rstrip('/')}/mcp"


async def list_tools() -> list[Tool]:
    """Discover available tools from the MCP server via the tools/list protocol."""
    async with streamable_http_client(_mcp_url()) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools


async def call_tool(name: str, arguments: dict | None = None) -> MCPServerResult:
    """Call a tool on the MCP server over HTTP and extract image/text content."""
    async with streamable_http_client(_mcp_url()) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments=arguments or {})

            image_base64 = None
            text = None
            for item in result.content:
                if getattr(item, "type", "") == "image":
                    image_base64 = item.data
                elif getattr(item, "type", "") == "text":
                    text = getattr(item, "text", None)

            return MCPServerResult(
                image_base64=image_base64,
                text=text,
                is_error=bool(result.isError),
                content=result.content,
            )
