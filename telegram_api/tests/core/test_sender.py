from unittest.mock import AsyncMock

import pytest
from telegram.constants import ParseMode
from telegram.error import BadRequest

from telegram_api.core.sender import send_agent_reply

DUMMY_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


@pytest.mark.asyncio
async def test_send_agent_reply_text_success():
    msg = AsyncMock()
    msg.reply_text = AsyncMock()

    await send_agent_reply(msg, "Olá **mundo**!")

    msg.reply_text.assert_called_once()
    args, kwargs = msg.reply_text.call_args
    assert args[0] == "Olá <b>mundo</b>!"
    assert kwargs.get("parse_mode") == ParseMode.HTML


@pytest.mark.asyncio
async def test_send_agent_reply_text_fallback_on_parse_error():
    msg = AsyncMock()
    # First call with HTML raises parse error, second call (fallback) succeeds
    msg.reply_text = AsyncMock(
        side_effect=[
            BadRequest("Can't parse entities: can't find end of the entity"),
            AsyncMock(),
        ]
    )

    await send_agent_reply(msg, "Texto com erro **não fechado")

    assert msg.reply_text.call_count == 2
    # Second call should be plain text without parse_mode
    second_call_args = msg.reply_text.call_args_list[1][0]
    second_call_kwargs = msg.reply_text.call_args_list[1][1]
    assert second_call_args[0] == "Texto com erro **não fechado"
    assert "parse_mode" not in second_call_kwargs


@pytest.mark.asyncio
async def test_send_agent_reply_photo_success():
    msg = AsyncMock()
    msg.reply_photo = AsyncMock()

    await send_agent_reply(msg, "Gráfico **semanal**", image_base64=DUMMY_PNG_B64)

    msg.reply_photo.assert_called_once()
    _, kwargs = msg.reply_photo.call_args
    assert kwargs.get("caption") == "Gráfico <b>semanal</b>"
    assert kwargs.get("parse_mode") == ParseMode.HTML
    assert kwargs.get("photo") is not None


@pytest.mark.asyncio
async def test_send_agent_reply_photo_fallback_on_parse_error():
    msg = AsyncMock()
    msg.reply_photo = AsyncMock(
        side_effect=[
            BadRequest("Can't parse entities: error"),
            AsyncMock(),
        ]
    )

    await send_agent_reply(msg, "Legenda com erro", image_base64=DUMMY_PNG_B64)

    assert msg.reply_photo.call_count == 2
    second_call_kwargs = msg.reply_photo.call_args_list[1][1]
    assert second_call_kwargs.get("caption") == "Legenda com erro"
    assert "parse_mode" not in second_call_kwargs


@pytest.mark.asyncio
async def test_send_agent_reply_propagates_non_parse_errors():
    msg = AsyncMock()
    msg.reply_text = AsyncMock(side_effect=BadRequest("chat not found"))

    with pytest.raises(BadRequest, match="chat not found"):
        await send_agent_reply(msg, "Olá")

    assert msg.reply_text.call_count == 1
