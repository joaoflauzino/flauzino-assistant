import functools
import logging
from typing import Any, Callable

import httpx

from core.exceptions import FinanceClientError, GraphGenerationError, ServiceError

logger = logging.getLogger(__name__)


def handle_service_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch unexpected errors in the Service Layer."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except (FinanceClientError, GraphGenerationError):
            raise
        except httpx.HTTPStatusError as e:
            raise FinanceClientError(
                f"Finance API returned status {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise FinanceClientError(f"Failed to connect to Finance API: {str(e)}")
        except Exception as e:
            logger.error(f"Internal service error: {e}", exc_info=True)
            raise ServiceError(f"Internal Server Error: {str(e)}")

    return wrapper
