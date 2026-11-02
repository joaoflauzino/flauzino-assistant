from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

from telegram_api.core.agent_client import send_receipt_to_agent
from telegram_api.core.correlation import set_request_id
from telegram_api.core.logger import get_logger
from telegram_api.services.agent_interaction import (
    InteractionMessages,
    handle_agent_interaction,
)

logger = get_logger(__name__)

PHOTO_MESSAGES = InteractionMessages(
    fallback="Recebi a imagem, mas não consegui processar. Tente enviar uma foto mais clara.",
    http_error=(
        "😔 Desculpe, tive um problema ao processar a imagem. "
        "Por favor, tente enviar outra foto."
    ),
    connection_error=(
        "⚠️ Não consegui conectar ao serviço de OCR. Por favor, tente novamente mais tarde."
    ),
    unexpected_error=(
        "❌ Ocorreu um erro ao processar a imagem. Por favor, tente enviar uma foto mais clara."
    ),
)


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages (receipts) from users."""
    if not update.message or not update.message.photo:
        return

    chat_id = update.effective_chat.id
    photo = update.message.photo[-1]

    set_request_id()
    logger.info(f"Received photo from chat {chat_id}")
    await update.message.chat.send_action("upload_photo")

    async def call(session_id: str | None) -> dict:
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = BytesIO()
        await photo_file.download_to_memory(photo_bytes)
        logger.info(
            f"Downloaded photo from chat {chat_id}, size: {len(photo_bytes.getvalue())} bytes"
        )
        await update.message.chat.send_action("typing")
        return await send_receipt_to_agent(
            file_content=photo_bytes.getvalue(),
            filename=f"receipt_{chat_id}.jpg",
            session_id=session_id,
        )

    await handle_agent_interaction(
        target_message=update.message,
        chat_id=chat_id,
        call=call,
        messages=PHOTO_MESSAGES,
    )
