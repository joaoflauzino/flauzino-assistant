from fastapi import Request
from fastapi.responses import JSONResponse

from core.exceptions import (
    FinanceClientError,
    GraphGenerationError,
    MCPServerError,
    ServiceError,
)


async def finance_client_error_handler(request: Request, exc: FinanceClientError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"message": "Finance API Error", "detail": exc.message},
    )


async def graph_generation_error_handler(
    request: Request, exc: GraphGenerationError
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"message": "Graph Generation Error", "detail": exc.message},
    )


async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": exc.message},
    )


async def mcp_server_error_handler(request: Request, exc: MCPServerError) -> JSONResponse:
    """Catch-all handler for any unhandled MCPServerError subclass."""
    return JSONResponse(
        status_code=500,
        content={"message": "MCP Server Error", "detail": exc.message},
    )
