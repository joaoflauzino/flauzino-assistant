from typing import Any, Callable

import functools
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException

from finance_api.core.exceptions import (
    DatabaseError,
    EntityConflictError,
    EntityNotFoundError,
    ServiceError,
    ValidationError,
)
from finance_api.core.logger import get_logger

logger = get_logger(__name__)


def handle_service_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch unexpected errors in Service Layer."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except IntegrityError:
            raise EntityConflictError("Resource already exists.")
        except SQLAlchemyError as e:
            raise DatabaseError(f"Database operation failed: {str(e)}")
        except EntityNotFoundError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.error(f"Internal service error: {e}", exc_info=True)
            raise ServiceError(f"Internal Server Error: {str(e)}")

    return wrapper
