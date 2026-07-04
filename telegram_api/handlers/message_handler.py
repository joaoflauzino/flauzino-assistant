from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
from telegram.constants import ParseMode
import httpx
import base64
import io

from telegram_api.core.http_client import send_message_to_agent
from telegram_api.core.logger import get_logger
from telegram_api.core.database import get_db
from telegram_api.repositories.session_repository import SessionRepository

logger = get_logger(__name__)


async def handle_unknown_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages from users when no specific command is given, showing available commands."""
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    logger.info(f"Received fallback text message from chat {chat_id}")

    commands_message = (
        "Desculpe, no momento não aceito mensagens de texto livre.\n\n"
        "Aqui estão os comandos disponíveis:\n"
        "/start - Iniciar o bot\n"
        "/help - Como usar o bot\n"
        "/gasto - Registrar um novo gasto passo a passo\n"
    )

    await update.message.reply_text(commands_message)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages from users using the AI agent."""
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
            response_data = await send_message_to_agent(user_message, session_id=session_id)

            # Extract the response message
            bot_response = response_data.get(
                "response", "Desculpe, não consegui processar sua mensagem."
            )

            # Check if flow is complete
            is_complete = response_data.get("is_complete", False)
            suggested_options = response_data.get("suggested_options")
            image_base64 = response_data.get("image_base64")

            if is_complete:
                await repo.delete_session(chat_id)
                logger.info(f"Session cleared for chat {chat_id} (task complete)")
            else:
                # Extract and save new session_id if not complete
                new_session_id = response_data.get("session_id")
                if new_session_id:
                    await repo.save_session(chat_id, new_session_id)

        # Send response back to user
        reply_markup = None
        if suggested_options and isinstance(suggested_options, list):
            keyboard = []
            row = []
            for option in suggested_options:
                row.append(InlineKeyboardButton(option, callback_data=f"agent_opt:{option}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            reply_markup = InlineKeyboardMarkup(keyboard)

        escaped_response = bot_response.replace("_", "\\_")

        try:
            if image_base64:
                image_data = base64.b64decode(image_base64)
                if reply_markup:
                    await update.message.reply_photo(
                        photo=io.BytesIO(image_data),
                        caption=escaped_response,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup,
                    )
                else:
                    await update.message.reply_photo(
                        photo=io.BytesIO(image_data),
                        caption=escaped_response,
                        parse_mode=ParseMode.MARKDOWN,
                    )
            else:
                if reply_markup:
                    await update.message.reply_text(
                        escaped_response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text(escaped_response, parse_mode=ParseMode.MARKDOWN)
        except BadRequest as e:
            if "parse" in str(e).lower() or "entities" in str(e).lower():
                logger.warning(f"Markdown parsing failed, falling back to plain text: {e}")
                await update.message.reply_text(bot_response)
            else:
                raise
        logger.info(f"Sent response to chat {chat_id}")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from agent_api: {e.response.status_code} - {e.response.text}")
        error_message = (
            "Desculpe, tive um problema ao processar sua solicitação. "
            "Por favor, tente novamente em alguns instantes."
        )
        await update.message.reply_text(error_message)

    except httpx.RequestError as e:
        logger.error(f"Connection error to agent_api: {e}")
        error_message = "Não consegui conectar ao serviço. Por favor, tente novamente mais tarde."
        await update.message.reply_text(error_message)

    except Exception as e:
        logger.error(f"Unexpected error handling message: {e}", exc_info=True)
        error_message = "Ocorreu um erro inesperado. Por favor, tente novamente."
        await update.message.reply_text(error_message)


async def handle_agent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks from agent's suggested options."""
    query = update.callback_query
    await query.answer()

    # Remove the prefix "agent_opt:"
    option_text = query.data[10:]
    logger.info(f"User clicked agent option: {option_text}")

    # Simulate a user message with the clicked option
    # We construct a fake message object or just call the same logic as handle_text_message
    # But since handle_text_message expects update.message.text, we can't easily fake it if update.message is empty
    # Wait, query.message is the bot's message.
    # We can just extract the logic of handle_text_message into a helper, or just manually do it here.

    chat_id = update.effective_chat.id

    # Send typing indicator
    if query.message:
        await query.message.chat.send_action("typing")

        # We append the user's choice to the chat visually
        await query.message.reply_text(f"Você selecionou: {option_text}")

    try:
        async with get_db() as session:
            repo = SessionRepository(session)
            session_id = await repo.get_session(chat_id)

            response_data = await send_message_to_agent(option_text, session_id=session_id)

            bot_response = response_data.get(
                "response", "Desculpe, não consegui processar sua mensagem."
            )
            is_complete = response_data.get("is_complete", False)
            suggested_options = response_data.get("suggested_options")
            image_base64 = response_data.get("image_base64")

            if is_complete:
                await repo.delete_session(chat_id)
            else:
                new_session_id = response_data.get("session_id")
                if new_session_id:
                    await repo.save_session(chat_id, new_session_id)

        reply_markup = None
        if suggested_options and isinstance(suggested_options, list):
            keyboard = []
            row = []
            for option in suggested_options:
                row.append(InlineKeyboardButton(option, callback_data=f"agent_opt:{option}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            reply_markup = InlineKeyboardMarkup(keyboard)

        escaped_response = bot_response.replace("_", "\\_")

        try:
            if image_base64:
                image_data = base64.b64decode(image_base64)
                if reply_markup:
                    await query.message.reply_photo(
                        photo=io.BytesIO(image_data),
                        caption=escaped_response,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup,
                    )
                else:
                    await query.message.reply_photo(
                        photo=io.BytesIO(image_data),
                        caption=escaped_response,
                        parse_mode=ParseMode.MARKDOWN,
                    )
            else:
                if reply_markup:
                    await query.message.reply_text(
                        escaped_response, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
                    )
                else:
                    await query.message.reply_text(escaped_response, parse_mode=ParseMode.MARKDOWN)
        except BadRequest as e:
            if "parse" in str(e).lower() or "entities" in str(e).lower():
                logger.warning(f"Markdown parsing failed: {e}")
                if reply_markup:
                    await query.message.reply_text(bot_response, reply_markup=reply_markup)
                else:
                    await query.message.reply_text(bot_response)
            else:
                raise

    except Exception as e:
        logger.error(f"Error handling agent callback: {e}", exc_info=True)
        if query.message:
            await query.message.reply_text("Ocorreu um erro ao processar sua seleção.")


agent_callback_handler = CallbackQueryHandler(handle_agent_callback, pattern="^agent_opt:")
