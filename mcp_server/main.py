from contextlib import asynccontextmanager

from fastapi import FastAPI
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from mcp_server.core.exceptions import (
    FinanceClientError,
    GraphGenerationError,
    MCPServerError,
    ServiceError,
)
from mcp_server.core.handlers import (
    finance_client_error_handler,
    graph_generation_error_handler,
    mcp_server_error_handler,
    service_error_handler,
)
from mcp_server.core.mcp import mcp
from mcp_server.routers import graphs

# Import mcp_service to trigger tool registration via decorators
import mcp_server.services.mcp_service  # noqa: F401

# Gerencia as sessões do transporte Streamable HTTP do protocolo MCP.
# O task group é criado no lifespan abaixo (requisito do StreamableHTTPSessionManager).
session_manager = StreamableHTTPSessionManager(
    app=mcp._mcp_server,
    json_response=mcp.settings.json_response,
    stateless=mcp.settings.stateless_http,
    security_settings=mcp.settings.transport_security,
)
streamable_http_app = StreamableHTTPASGIApp(session_manager)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Manage the MCP Streamable HTTP session manager lifecycle."""
    async with session_manager.run():
        yield


app = FastAPI(title="MCP Graph Server", lifespan=lifespan)

# Register global exception handlers
app.add_exception_handler(FinanceClientError, finance_client_error_handler)
app.add_exception_handler(GraphGenerationError, graph_generation_error_handler)
app.add_exception_handler(ServiceError, service_error_handler)
app.add_exception_handler(MCPServerError, mcp_server_error_handler)

# Register routers
app.include_router(graphs.router)

# Mount Streamable HTTP transport for the MCP protocol
# Endpoints: POST/GET/DELETE /mcp
app.mount("/mcp", streamable_http_app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
