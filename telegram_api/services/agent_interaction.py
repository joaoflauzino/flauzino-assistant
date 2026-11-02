"""Common flow for handlers that talk to the AI agent: session, reply and error mapping."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from telegram_api.core.formatter import build_options_keyboard
from telegram_api.core.logger import get_logger
from telegram_api.core.sender import send_agent_reply
from telegram_api.services.session_service import SessionService

logger = get_logger(__name__)

type AgentCall = Callable[[str | None], Awaitable[dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class InteractionMessages:
    """User-facing texts used when the agent reply is missing or the call fails."""

    fallback: str
    http_error: str
    connection_error: str
    unexpected_error: str


async def run_agent_call(chat_id: int, call: AgentCall) -> dict[str, Any]:
    """Runs one agent call bound to the chat session and syncs the session afterwards."""
    session_id = await SessionService.get_session(chat_id)
    response_data = await call(session_id)
    await SessionService.sync_session(chat_id, response_data)
    return response_data


async def reply_with_response(
    target_message: Any,
    response_data: dict[str, Any],
    messages: InteractionMessages,
    *,
    with_options: bool = False,
) -> None:
    """Sends the agent reply, optionally attaching the suggested-options keyboard."""
    reply_markup = None
    if with_options:
        reply_markup = build_options_keyboard(response_data.get("suggested_options"))

    await send_agent_reply(
        target_message=target_message,
        text=response_data.get("response", messages.fallback),
        image_base64=response_data.get("image_base64"),
        reply_markup=reply_markup,
    )


async def handle_agent_interaction(
    target_message: Any,
    chat_id: int,
    call: AgentCall,
    messages: InteractionMessages,
    *,
    with_options: bool = False,
) -> None:
    """Runs the agent call and replies, translating transport failures into user messages."""
    try:
        response_data = await run_agent_call(chat_id, call)
        await reply_with_response(
            target_message, response_data, messages, with_options=with_options
        )
        logger.info(f"Sent agent response to chat {chat_id}")
    except httpx.HTTPStatusError as error:
        logger.error(
            f"HTTP error from agent_api: {error.response.status_code} - {error.response.text}"
        )
        await target_message.reply_text(messages.http_error)
    except httpx.RequestError as error:
        logger.error(f"Connection error to agent_api: {error}")
        await target_message.reply_text(messages.connection_error)
    except Exception as error:  # Boundary: never leave the chat without an answer.
        logger.error(f"Unexpected error handling agent interaction: {error}", exc_info=True)
        await target_message.reply_text(messages.unexpected_error)
