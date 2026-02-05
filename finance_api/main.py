from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from finance_api.routers import limits, spents, categories, payment_methods, payment_owners
from finance_api.core.exceptions import (
    DatabaseError,
    EntityConflictError,
    EntityNotFoundError,
    ServiceError,
    LimitServiceError,
    SpentServiceError,
    PaymentMethodServiceError,
    PaymentOwnerServiceError,
    ValidationError,
)
from finance_api.core.handlers import (
    database_error_handler,
    entity_conflict_handler,
    entity_not_found_handler,
    service_error_handler,
    limit_service_error_handler,
    spent_service_error_handler,
    payment_method_service_error_handler,
    payment_owner_service_error_handler,
    validation_error_handler,
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
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(ServiceError, service_error_handler)
app.add_exception_handler(LimitServiceError, limit_service_error_handler)
app.add_exception_handler(SpentServiceError, spent_service_error_handler)
app.add_exception_handler(PaymentMethodServiceError, payment_method_service_error_handler)
app.add_exception_handler(PaymentOwnerServiceError, payment_owner_service_error_handler)

app.include_router(spents.router, prefix="/spents", tags=["spents"])
app.include_router(limits.router, prefix="/limits", tags=["limits"])
app.include_router(categories.router, prefix="/categories", tags=["categories"])
app.include_router(payment_methods.router, prefix="/payment-methods", tags=["payment-methods"])
app.include_router(payment_owners.router, prefix="/payment-owners", tags=["payment-owners"])
