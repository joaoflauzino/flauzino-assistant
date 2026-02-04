from fastapi import Request
from fastapi.responses import JSONResponse

from finance_api.core.exceptions import (
    DatabaseError,
    EntityConflictError,
    EntityNotFoundError,
    ServiceError,
    LimitServiceError,
    SpentServiceError,
    ValidationError,
)


async def database_error_handler(request: Request, exc: DatabaseError):
    return JSONResponse(
        status_code=500,
        content={"message": "Database Error", "detail": str(exc)},
    )


async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"message": "Not Found", "detail": str(exc)},
    )


async def entity_conflict_handler(request: Request, exc: EntityConflictError):
    return JSONResponse(
        status_code=409,
        content={"message": "Conflict", "detail": str(exc)},
    )


async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"message": "Validation Error", "detail": str(exc)},
    )


async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


async def limit_service_error_handler(request: Request, exc: LimitServiceError):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


async def spent_service_error_handler(request: Request, exc: SpentServiceError):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )
