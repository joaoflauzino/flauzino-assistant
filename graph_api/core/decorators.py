import functools
import logging
from typing import Any, Callable

from graph_api.core.exceptions import GraphGenerationError, ServiceError

logger = logging.getLogger(__name__)


def handle_service_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch unexpected errors in the Service Layer."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except GraphGenerationError:
            raise
        except Exception as e:
            logger.error(f"Internal service error: {e}", exc_info=True)
            raise ServiceError(f"Internal Server Error: {str(e)}")

    return wrapper
