from fastapi import Request
from fastapi.responses import JSONResponse

from graph_api.core.exceptions import (
    GraphAPIError,
    GraphGenerationError,
    ServiceError,
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


async def graph_api_error_handler(request: Request, exc: GraphAPIError) -> JSONResponse:
    """Catch-all handler for any unhandled GraphAPIError subclass."""
    return JSONResponse(
        status_code=500,
        content={"message": "Graph API Error", "detail": exc.message},
    )
