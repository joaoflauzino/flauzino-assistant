from fastapi import Request
from fastapi.responses import JSONResponse

from agent_api.core.exceptions import (
    FinanceServerError,
    FinanceUnreachableError,
    InvalidSpentError,
    LLMProviderError,
    LLMParsingError,
    LLMUnknownError,
    DatabaseError,
)


async def finance_unreachable_handler(request: Request, exc: FinanceUnreachableError):
    return JSONResponse(
        status_code=503,
        content={"message": "Service unavailable", "detail": str(exc)},
    )


async def invalid_spent_handler(request: Request, exc: InvalidSpentError):
    return JSONResponse(
        status_code=400,
        content={"message": "Invalid data", "detail": str(exc)},
    )


async def finance_server_error_handler(request: Request, exc: FinanceServerError):
    return JSONResponse(
        status_code=502,
        content={"message": "Upstream error", "detail": str(exc)},
    )


async def llm_provider_handler(request: Request, exc: LLMProviderError):
    return JSONResponse(
        status_code=503,
        content={"message": "AI Service Temporarily Unavailable", "detail": str(exc)},
    )


async def llm_parsing_handler(request: Request, exc: LLMParsingError):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


async def llm_unknown_handler(request: Request, exc: LLMUnknownError):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


async def database_error_handler(request: Request, exc: DatabaseError):
    return JSONResponse(
        status_code=500,
        content={"message": "Database Error", "detail": str(exc)},
    )
