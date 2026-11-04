from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from langchain_core.language_models.chat_models import BaseChatModel

from agent_api.core.exceptions import FinanceUnreachableError
from agent_api.services.agent import AgentService
from agent_api.services.clients.finance import FinanceService
from agent_api.services.clients.graph import GraphService
from agent_api.services.system_prompt import (
    PromptMetadata,
    build_system_prompt,
)

SP_TZ = ZoneInfo("America/Sao_Paulo")


def test_prompt_metadata_formats_collections_and_dates() -> None:
    metadata = PromptMetadata.from_collections(
        ["mercado", "lazer"],
        ["salario"],
        ["pix"],
        ["itau_joao"],
        ["c6_card"],
        now=datetime(2026, 8, 15, 10, 0, tzinfo=SP_TZ),
    )

    assert metadata.valid_categories == "'mercado', 'lazer'"
    assert metadata.today_date == "2026-08-15"
    assert metadata.current_year_month == "2026-08"


def test_build_system_prompt_uses_platform_instructions() -> None:
    metadata = PromptMetadata.empty()

    telegram_prompt = build_system_prompt(metadata, "telegram")
    web_prompt = build_system_prompt(metadata, "web")
    default_prompt = build_system_prompt(metadata)

    assert "Formatação para Telegram" in telegram_prompt
    assert "Formatação para Web" not in telegram_prompt
    assert "Formatação para Web" in web_prompt
    assert "Formatação para Telegram" not in default_prompt
    assert "Formatação para Web" not in default_prompt


def test_build_system_prompt_unknown_platform_has_no_instructions() -> None:
    prompt = build_system_prompt(PromptMetadata.empty(), "desktop")

    assert "Formatação para" not in prompt


@pytest.mark.asyncio
async def test_agent_service_prompt_falls_back_when_metadata_fails() -> None:
    finance_service = AsyncMock(spec=FinanceService)
    finance_service.get_categories.side_effect = FinanceUnreachableError("offline")
    service = AgentService(
        llm=MagicMock(spec=BaseChatModel),
        finance_service=finance_service,
        graph_service=AsyncMock(spec=GraphService),
    )

    prompt = await service.get_system_prompt(platform="telegram")

    assert "CATEGORIAS DE GASTOS VÁLIDAS" in prompt
    assert "[]" in prompt
    assert "Formatação para Telegram" in prompt
