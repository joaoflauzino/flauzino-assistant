import httpx
from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from telegram_api.core.correlation import set_request_id
from telegram_api.core.formatter import build_options_keyboard, send_agent_reply
from telegram_api.core.http_client import send_message_to_agent
from telegram_api.core.logger import get_logger
from telegram_api.services.session_service import SessionService

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

    set_request_id()
    logger.info(f"Received message from chat {chat_id}: {user_message[:50]}...")

    # Send typing indicator
    await update.message.chat.send_action("typing")

    try:
        session_id = await SessionService.get_session(chat_id)

        # Call agent_api
        response_data = await send_message_to_agent(user_message, session_id=session_id)

        bot_response = response_data.get(
            "response", "Desculpe, não consegui processar sua mensagem."
        )
        suggested_options = response_data.get("suggested_options")
        image_base64 = response_data.get("image_base64")

        # Sync session state
        await SessionService.sync_session(chat_id, response_data)

        # Build options keyboard if options are suggested
        reply_markup = build_options_keyboard(suggested_options)

        await send_agent_reply(
            target_message=update.message,
            text=bot_response,
            image_base64=image_base64,
            reply_markup=reply_markup,
        )
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
    set_request_id()
    logger.info(f"User clicked agent option: {option_text}")

    chat_id = update.effective_chat.id

    # Send typing indicator
    if query.message:
        await query.message.chat.send_action("typing")
        await query.message.reply_text(f"Você selecionou: {option_text}")

    try:
        session_id = await SessionService.get_session(chat_id)

        response_data = await send_message_to_agent(option_text, session_id=session_id)

        bot_response = response_data.get(
            "response", "Desculpe, não consegui processar sua mensagem."
        )
        suggested_options = response_data.get("suggested_options")
        image_base64 = response_data.get("image_base64")

        # Sync session state
        await SessionService.sync_session(chat_id, response_data)

        reply_markup = build_options_keyboard(suggested_options)

        await send_agent_reply(
            target_message=query.message,
            text=bot_response,
            image_base64=image_base64,
            reply_markup=reply_markup,
        )

    except Exception as e:
        logger.error(f"Error handling agent callback: {e}", exc_info=True)
        if query.message:
            await query.message.reply_text("Ocorreu um erro ao processar sua seleção.")


agent_callback_handler = CallbackQueryHandler(handle_agent_callback, pattern="^agent_opt:")
