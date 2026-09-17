import functools
from typing import Any, Callable

from fastapi import HTTPException
from google.api_core.exceptions import GoogleAPIError
import httpx
from langchain_core.exceptions import OutputParserException
from sqlalchemy.exc import SQLAlchemyError

from agent_api.core.exceptions import (
    AudioProcessingError,
    DatabaseError,
    FinanceServerError,
    FinanceUnreachableError,
    InvalidAudioError,
    InvalidImageError,
    InvalidSpentError,
    LLMParsingError,
    LLMProviderError,
    OCRProcessingError,
    ServiceError,
)
from agent_api.core.logger import get_logger

logger = get_logger(__name__)


def handle_finance_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch httpx errors and raise FinanceService implementation errors."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except (ServiceError, HTTPException):
            raise
        except httpx.RequestError:
            raise FinanceUnreachableError("Finance API is offline or unreachable")
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 422 or status == 400:
                raise InvalidSpentError(f"Invalid data: {e.response.text}")
            if status >= 500:
                raise FinanceServerError("Finance API internal error")
            raise
        except Exception as e:
            logger.error(f"Unexpected finance error: {e}", exc_info=True)
            raise ServiceError(f"Unexpected finance error: {str(e)}")

    return wrapper


def handle_llm_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch LLM errors and raise LLMService implementation errors."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except (ServiceError, HTTPException):
            raise
        except OutputParserException as e:
            raise LLMParsingError(f"Failed to parse LLM response: {str(e)}")
        except GoogleAPIError as e:
            raise LLMProviderError(f"Google Gemini Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected LLM error: {e}", exc_info=True)
            raise ServiceError(f"Unexpected LLM Error: {str(e)}")

    return wrapper


def handle_service_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Generic decorator to catch unexpected errors in Service Layer."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except (ServiceError, HTTPException):
            raise
        except SQLAlchemyError as e:
            raise DatabaseError(f"Database operation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected service error: {e}", exc_info=True)
            raise ServiceError(f"Unexpected error: {str(e)}")

    return wrapper


def handle_ocr_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch OCR errors and raise OCRService implementation errors."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except (ServiceError, HTTPException):
            raise
        except Exception as e:
            logger.error(f"Unexpected OCR error: {e}", exc_info=True)
            error_msg = str(e).lower()
            if any(word in error_msg for word in ["image", "decode", "format", "invalid"]):
                raise InvalidImageError(f"Invalid image: {str(e)}")

            raise OCRProcessingError(f"OCR processing failed: {str(e)}")

    return wrapper


def handle_audio_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch audio processing errors and raise AudioProcessingError."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except (AudioProcessingError, InvalidAudioError, HTTPException):
            raise
        except Exception as e:
            logger.error(f"Unexpected Audio error: {e}", exc_info=True)
            raise AudioProcessingError(f"Falha ao transcrever o áudio: {str(e)}")

    return wrapper


def handle_tool_errors(tool_name: str | None = None) -> Callable[..., Any]:
    """Decorator to catch exceptions inside LangChain tools and return graceful error messages."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = tool_name or func.__name__
            try:
                return await func(*args, **kwargs)
            except ServiceError as e:
                logger.error(f"Erro de serviço na tool {name}: {e}")
                err_text = e.message if hasattr(e, "message") else str(e)
                return f"Erro na operação de {name}: {err_text}"
            except Exception as e:
                logger.error(f"Erro inesperado na tool {name}: {e}", exc_info=True)
                return f"Não foi possível completar a ação em {name} devido a uma instabilidade temporária."

        return wrapper

    return decorator
