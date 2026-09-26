from io import BytesIO

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from telegram_api.core.correlation import set_request_id
from telegram_api.core.formatter import send_agent_reply
from telegram_api.core.http_client import send_audio_to_agent
from telegram_api.core.logger import get_logger
from telegram_api.services.session_service import SessionService

logger = get_logger(__name__)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages and audio files from users."""
    if not update.message:
        return

    # Can be a voice note or an audio file
    media_item = update.message.voice or update.message.audio
    if not media_item:
        return

    chat_id = update.effective_chat.id
    mime_type = media_item.mime_type or "audio/ogg"

    set_request_id()
    logger.info(f"Received audio/voice from chat {chat_id} with mime {mime_type}")

    # Send recording audio indicator to signify we are processing
    await update.message.chat.send_action("record_audio")

    try:
        session_id = await SessionService.get_session(chat_id)

        # Download the audio file
        audio_file = await context.bot.get_file(media_item.file_id)
        audio_bytes = BytesIO()
        await audio_file.download_to_memory(audio_bytes)
        audio_bytes.seek(0)

        logger.info(
            f"Downloaded audio from chat {chat_id}, size: {len(audio_bytes.getvalue())} bytes"
        )

        # Send typing indicator while LLM processes transcription and response
        await update.message.chat.send_action("typing")

        # Send to agent_api
        response_data = await send_audio_to_agent(
            file_content=audio_bytes.getvalue(),
            filename=f"audio_{chat_id}.ogg",
            content_type=mime_type,
            session_id=session_id,
        )

        # Extract the response message
        bot_response = response_data.get(
            "response",
            "Recebi o áudio, mas não consegui processar o conteúdo. Tente falar novamente.",
        )

        # Sync session state
        await SessionService.sync_session(chat_id, response_data)

        # Send response back to user
        await send_agent_reply(target_message=update.message, text=bot_response)
        logger.info(f"Sent audio processed response to chat {chat_id}")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from agent_api: {e.response.status_code} - {e.response.text}")
        error_message = (
            "😔 Desculpe, tive um problema ao processar o áudio. "
            "Por favor, tente enviar novamente em alguns instantes."
        )
        await update.message.reply_text(error_message)

    except httpx.RequestError as e:
        logger.error(f"Connection error to agent_api: {e}")
        error_message = (
            "⚠️ Não consegui conectar ao serviço de processamento. "
            "Por favor, tente novamente mais tarde."
        )
        await update.message.reply_text(error_message)

    except Exception as e:
        logger.error(f"Unexpected error handling audio: {e}", exc_info=True)
        error_message = "❌ Ocorreu um erro ao processar o áudio. Por favor, tente novamente."
        await update.message.reply_text(error_message)
