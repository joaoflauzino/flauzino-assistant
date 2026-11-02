from telegram import Message, Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from telegram_api.core.agent_client import send_message_to_agent
from telegram_api.core.correlation import set_request_id
from telegram_api.core.logger import get_logger
from telegram_api.services.agent_interaction import (
    InteractionMessages,
    handle_agent_interaction,
    reply_with_response,
    run_agent_call,
)

logger = get_logger(__name__)

TEXT_MESSAGES = InteractionMessages(
    fallback="Desculpe, não consegui processar sua mensagem.",
    http_error=(
        "Desculpe, tive um problema ao processar sua solicitação. "
        "Por favor, tente novamente em alguns instantes."
    ),
    connection_error="Não consegui conectar ao serviço. Por favor, tente novamente mais tarde.",
    unexpected_error="Ocorreu um erro inesperado. Por favor, tente novamente.",
)

CALLBACK_MESSAGES = InteractionMessages(
    fallback="Desculpe, não consegui processar sua mensagem.",
    http_error="Ocorreu um erro ao processar sua seleção.",
    connection_error="Ocorreu um erro ao processar sua seleção.",
    unexpected_error="Ocorreu um erro ao processar sua seleção.",
)


async def handle_unknown_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages from users when no specific command is given, showing available commands."""
    if not update.message or not update.message.text:
        return

    chat = update.effective_chat
    if chat is None:
        return

    chat_id = chat.id
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

    message = update.message
    chat = update.effective_chat
    if message is None or message.text is None or chat is None:
        return

    user_message = message.text
    chat_id = chat.id

    set_request_id()
    logger.info(f"Received message from chat {chat_id}: {user_message[:50]}...")

    await message.chat.send_action("typing")
    await handle_agent_interaction(
        target_message=message,
        chat_id=chat_id,
        call=lambda session_id: send_message_to_agent(user_message, session_id=session_id),
        messages=TEXT_MESSAGES,
        with_options=True,
    )


async def handle_agent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks from agent's suggested options."""
    query = update.callback_query
    chat = update.effective_chat
    message = query.message if query is not None else None
    if query is None or chat is None or not isinstance(message, Message):
        return

    await query.answer()

    # Remove the prefix "agent_opt:"
    option_text = (query.data or "")[10:]
    set_request_id()
    logger.info(f"User clicked agent option: {option_text}")

    chat_id = chat.id
    await message.chat.send_action("typing")
    await message.reply_text(f"Você selecionou: {option_text}")

    try:
        response_data = await run_agent_call(
            chat_id,
            lambda session_id: send_message_to_agent(option_text, session_id=session_id),
        )
        await reply_with_response(message, response_data, CALLBACK_MESSAGES, with_options=True)
    except Exception as error:  # Boundary: keep the callback responsive.
        logger.error(f"Error handling agent callback: {error}", exc_info=True)
        await message.reply_text(CALLBACK_MESSAGES.unexpected_error)


agent_callback_handler = CallbackQueryHandler(handle_agent_callback, pattern="^agent_opt:")
