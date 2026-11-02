from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

from telegram_api.core.agent_client import send_audio_to_agent
from telegram_api.core.correlation import set_request_id
from telegram_api.core.logger import get_logger
from telegram_api.services.agent_interaction import (
    InteractionMessages,
    handle_agent_interaction,
)

logger = get_logger(__name__)

VOICE_MESSAGES = InteractionMessages(
    fallback="Recebi o áudio, mas não consegui processar o conteúdo. Tente falar novamente.",
    http_error=(
        "😔 Desculpe, tive um problema ao processar o áudio. "
        "Por favor, tente enviar novamente em alguns instantes."
    ),
    connection_error=(
        "⚠️ Não consegui conectar ao serviço de processamento. "
        "Por favor, tente novamente mais tarde."
    ),
    unexpected_error="❌ Ocorreu um erro ao processar o áudio. Por favor, tente novamente.",
)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages and audio files from users."""
    message = update.message
    if message is None:
        return

    # Can be a voice note or an audio file
    media_item = message.voice or message.audio
    if not media_item:
        return

    chat = update.effective_chat
    if chat is None:
        return

    chat_id = chat.id
    mime_type = media_item.mime_type or "audio/ogg"

    set_request_id()
    logger.info(f"Received audio/voice from chat {chat_id} with mime {mime_type}")
    await message.chat.send_action("record_audio")

    async def call(session_id: str | None) -> dict:
        audio_file = await context.bot.get_file(media_item.file_id)
        audio_bytes = BytesIO()
        await audio_file.download_to_memory(audio_bytes)
        logger.info(
            f"Downloaded audio from chat {chat_id}, size: {len(audio_bytes.getvalue())} bytes"
        )
        await message.chat.send_action("typing")
        return await send_audio_to_agent(
            file_content=audio_bytes.getvalue(),
            filename=f"audio_{chat_id}.ogg",
            content_type=mime_type,
            session_id=session_id,
        )

    await handle_agent_interaction(
        target_message=message,
        chat_id=chat_id,
        call=call,
        messages=VOICE_MESSAGES,
    )
