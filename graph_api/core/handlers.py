from fastapi import Request
from fastapi.responses import JSONResponse


async def graph_generation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"message": "Graph Generation Error", "detail": str(exc)},
    )


async def service_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


async def graph_api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for any unhandled GraphAPIError subclass."""
    return JSONResponse(
        status_code=500,
        content={"message": "Graph API Error", "detail": str(exc)},
    )
