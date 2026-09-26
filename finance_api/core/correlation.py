"""Correlation ID context manager and helpers."""

from contextvars import ContextVar
import uuid

CORRELATION_HEADER = "X-Request-ID"

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Retrieve the current request ID from context."""
    return _request_id_ctx.get()


def set_request_id(request_id: str | None = None) -> str:
    """Set or generate a new request ID for the current context.

    Args:
        request_id: Optional string ID. If None or empty, generates a UUIDv4.

    Returns:
        The active request ID string.
    """
    req_id = request_id.strip() if request_id and request_id.strip() else str(uuid.uuid4())
    _request_id_ctx.set(req_id)
    return req_id


def clear_request_id() -> None:
    """Clear the request ID from the current context."""
    _request_id_ctx.set("")
