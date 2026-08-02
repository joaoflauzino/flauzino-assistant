from fastapi import FastAPI

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
from mcp_server.routers import graphs
from mcp_server.routers.mcp import get_sse_transport, router as mcp_router

# Import mcp_service to trigger tool registration via decorators
import mcp_server.services.mcp_service  # noqa: F401

app = FastAPI(title="MCP Graph Server")

# Register global exception handlers
app.add_exception_handler(FinanceClientError, finance_client_error_handler)
app.add_exception_handler(GraphGenerationError, graph_generation_error_handler)
app.add_exception_handler(ServiceError, service_error_handler)
app.add_exception_handler(MCPServerError, mcp_server_error_handler)

# Register routers
app.include_router(graphs.router)
app.include_router(mcp_router)

# Mount SSE transport for MCP protocol
app.mount("/messages/", get_sse_transport().handle_post_message)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
