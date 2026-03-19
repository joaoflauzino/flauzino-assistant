from telegram import Update
from telegram.ext import ContextTypes
import httpx

from telegram_api.core.http_client import send_message_to_agent
from telegram_api.core.logger import get_logger
from telegram_api.core.database import get_db
from telegram_api.repositories.session_repository import SessionRepository

logger = get_logger(__name__)


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle text messages from users."""
    if not update.message or not update.message.text:
        return

    user_message = update.message.text
    chat_id = update.effective_chat.id

    logger.info(f"Received message from chat {chat_id}: {user_message[:50]}...")

    # Send typing indicator
    await update.message.chat.send_action("typing")

    try:
        async with get_db() as session:
            repo = SessionRepository(session)

            # Get existing session_id
            session_id = await repo.get_session(chat_id)

            # Call agent_api
            response_data = await send_message_to_agent(
                user_message, session_id=session_id
            )

            # Extract the response message
            bot_response = response_data.get(
                "response", "Desculpe, não consegui processar sua mensagem."
            )

            # Check if flow is complete
            is_complete = response_data.get("is_complete", False)

            if is_complete:
                await repo.delete_session(chat_id)
                logger.info(f"Session cleared for chat {chat_id} (task complete)")
            else:
                # Extract and save new session_id if not complete
                new_session_id = response_data.get("session_id")
                if new_session_id:
                    await repo.save_session(chat_id, new_session_id)

        # Send response back to user
        from telegram.error import BadRequest
        from telegram.constants import ParseMode
        
        # Escape underscores to prevent Markdown parser from interpreting them as unclosed italics
        escaped_response = bot_response.replace("_", "\\_")
        
        try:
            await update.message.reply_text(escaped_response, parse_mode=ParseMode.MARKDOWN)
        except BadRequest as e:
            if "parse" in str(e).lower() or "entities" in str(e).lower():
                logger.warning(f"Markdown parsing failed, falling back to plain text: {e}")
                await update.message.reply_text(bot_response)
            else:
                raise
        logger.info(f"Sent response to chat {chat_id}")

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error from agent_api: {e.response.status_code} - {e.response.text}"
        )
        error_message = (
            "😔 Desculpe, tive um problema ao processar sua solicitação. "
            "Por favor, tente novamente em alguns instantes."
        )
        await update.message.reply_text(error_message)

    except httpx.RequestError as e:
        logger.error(f"Connection error to agent_api: {e}")
        error_message = (
            "⚠️ Não consegui conectar ao serviço. Por favor, tente novamente mais tarde."
        )
        await update.message.reply_text(error_message)

    except Exception as e:
        logger.error(f"Unexpected error handling message: {e}", exc_info=True)
        error_message = "❌ Ocorreu um erro inesperado. Por favor, tente novamente."
        await update.message.reply_text(error_message)
