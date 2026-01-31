from typing import Any, Callable
import functools
import httpx
from langchain_core.exceptions import OutputParserException
from google.api_core.exceptions import GoogleAPIError
from sqlalchemy.exc import SQLAlchemyError


from agent_api.core.exceptions import (
    FinanceUnreachableError,
    FinanceServerError,
    InvalidSpentError,
    LLMProviderError,
    LLMParsingError,
    LLMUnknownError,
    DatabaseError,
)


def handle_finance_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch httpx errors and raise FinanceService implementation errors."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except httpx.RequestError:
            raise FinanceUnreachableError("Finance API is offline or unreachable")
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 422 or status == 400:
                raise InvalidSpentError(f"Invalid data: {e.response.text}")
            if status >= 500:
                raise FinanceServerError("Finance API internal error")
            raise

    return wrapper


def handle_llm_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch LLM errors and raise LLMService implementation errors."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except OutputParserException as e:
            raise LLMParsingError(f"Failed to parse LLM response: {str(e)}")
        except GoogleAPIError as e:
            raise LLMProviderError(f"Google Gemini Error: {str(e)}")
        except Exception as e:
            raise LLMUnknownError(f"Unexpected LLM Error: {str(e)}")

    return wrapper


def handle_chat_service_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch unexpected errors in ChatService."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except SQLAlchemyError as e:
            raise DatabaseError(f"Database operation failed: {str(e)}")

    return wrapper
