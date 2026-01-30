from fastapi import Request
from fastapi.responses import JSONResponse

from finance_api.core.exceptions import DatabaseError, EntityNotFoundError


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
