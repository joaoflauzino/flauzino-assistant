import json
from unittest.mock import MagicMock

import pytest

from finance_api.core.exceptions import (
    DatabaseError,
    EntityConflictError,
    EntityNotFoundError,
    ServiceError,
    ValidationError,
)
from finance_api.core.handlers import (
    database_error_handler,
    entity_conflict_handler,
    entity_not_found_handler,
    service_error_handler,
    validation_error_handler,
)


@pytest.mark.parametrize(
    ("handler", "exception", "status", "message"),
    [
        (database_error_handler, DatabaseError("db unavailable"), 500, "Database Error"),
        (
            entity_not_found_handler,
            EntityNotFoundError("missing"),
            404,
            "Not Found",
        ),
        (
            entity_conflict_handler,
            EntityConflictError("duplicate"),
            409,
            "Conflict",
        ),
        (validation_error_handler, ValidationError("invalid"), 422, "Validation Error"),
        (service_error_handler, ServiceError("failed"), 500, "Internal Server Error"),
    ],
)
@pytest.mark.asyncio
async def test_exception_handlers_return_status_and_details(
    handler,
    exception: Exception,
    status: int,
    message: str,
) -> None:
    response = await handler(MagicMock(), exception)

    assert response.status_code == status
    assert json.loads(response.body) == {"message": message, "detail": str(exception)}
