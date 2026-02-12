from telegram import Update
from telegram.ext import ContextTypes
import httpx
from io import BytesIO

from telegram_api.core.http_client import send_receipt_to_agent
from telegram_api.core.logger import get_logger

logger = get_logger(__name__)


async def handle_photo_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle photo messages (receipts) from users."""
    if not update.message or not update.message.photo:
        return

    chat_id = update.effective_chat.id
    session_id = f"telegram_{chat_id}"

    logger.info(f"Received photo from chat {chat_id}")

    # Send upload indicator
    await update.message.chat.send_action("upload_photo")

    try:
        # Get the highest resolution photo
        photo = update.message.photo[-1]

        # Download the photo
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = BytesIO()
        await photo_file.download_to_memory(photo_bytes)
        photo_bytes.seek(0)

        logger.info(
            f"Downloaded photo from chat {chat_id}, size: {len(photo_bytes.getvalue())} bytes"
        )

        # Send typing indicator while processing
        await update.message.chat.send_action("typing")

        # Send to agent_api for OCR processing
        response_data = await send_receipt_to_agent(
            file_content=photo_bytes.getvalue(),
            filename=f"receipt_{chat_id}.jpg",
            session_id=session_id,
        )

        # Extract the response message
        bot_response = response_data.get(
            "response",
            "Recebi a imagem, mas não consegui processar. Tente enviar uma foto mais clara.",
        )

        # Send response back to user
        await update.message.reply_text(bot_response)
        logger.info(f"Sent OCR response to chat {chat_id}")

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error from agent_api: {e.response.status_code} - {e.response.text}"
        )
        error_message = (
            "😔 Desculpe, tive um problema ao processar a imagem. "
            "Por favor, tente enviar outra foto."
        )
        await update.message.reply_text(error_message)

    except httpx.RequestError as e:
        logger.error(f"Connection error to agent_api: {e}")
        error_message = (
            "⚠️ Não consegui conectar ao serviço de OCR. "
            "Por favor, tente novamente mais tarde."
        )
        await update.message.reply_text(error_message)

    except Exception as e:
        logger.error(f"Unexpected error handling photo: {e}", exc_info=True)
        error_message = (
            "❌ Ocorreu um erro ao processar a imagem. "
            "Por favor, tente enviar uma foto mais clara."
        )
        await update.message.reply_text(error_message)
