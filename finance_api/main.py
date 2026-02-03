from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from finance_api.routers import limits, spents
from finance_api.core.exceptions import (
    DatabaseError,
    EntityConflictError,
    EntityNotFoundError,
    ServiceError,
    LimitServiceError,
    SpentServiceError,
)
from finance_api.core.handlers import (
    database_error_handler,
    entity_conflict_handler,
    entity_not_found_handler,
    service_error_handler,
    limit_service_error_handler,
    spent_service_error_handler,
)

app = FastAPI(title="Flauzino Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(DatabaseError, database_error_handler)
app.add_exception_handler(EntityNotFoundError, entity_not_found_handler)
app.add_exception_handler(EntityConflictError, entity_conflict_handler)
app.add_exception_handler(ServiceError, service_error_handler)
app.add_exception_handler(LimitServiceError, limit_service_error_handler)
app.add_exception_handler(SpentServiceError, spent_service_error_handler)

app.include_router(spents.router, prefix="/spents", tags=["spents"])
app.include_router(limits.router, prefix="/limits", tags=["limits"])
