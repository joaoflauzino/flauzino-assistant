from typing import Any, Callable

import functools
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException

from finance_api.core.exceptions import (
    DatabaseError,
    EntityConflictError,
    EntityNotFoundError,
)


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
        except Exception as e:
            # Re-raise HTTPException as is
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=500, detail=f"Internal Server Error: {str(e)}"
            )

    return wrapper
