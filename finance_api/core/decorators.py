from typing import Any, Callable

import functools
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException

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


def handle_limits_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch unexpected errors in Limits Service."""

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
            logger.error(f"Limit service error: {e}", exc_info=True)
            raise LimitServiceError(f"Internal Server Error: {str(e)}")

    return wrapper


def handle_spents_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch unexpected errors in Spents Service."""

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
            logger.error(f"Spent service error: {e}", exc_info=True)
            raise SpentServiceError(f"Internal Server Error: {str(e)}")

    return wrapper


def handle_payment_method_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch unexpected errors in Payment Method Service."""

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
            logger.error(f"Payment method service error: {e}", exc_info=True)
            raise PaymentMethodServiceError(f"Internal Server Error: {str(e)}")

    return wrapper


def handle_payment_owner_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch unexpected errors in Payment Owner Service."""

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
            logger.error(f"Payment owner service error: {e}", exc_info=True)
            raise PaymentOwnerServiceError(f"Internal Server Error: {str(e)}")

    return wrapper
