from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.language_models.chat_models import BaseChatModel

from agent_api.services.agent import AgentService
from agent_api.services.finance import FinanceService
from agent_api.services.graph import GraphService


@pytest.fixture
def mock_llm():
    return MagicMock(spec=BaseChatModel)


@pytest.fixture
def mock_finance_service():
    service = AsyncMock(spec=FinanceService)
    service.get_categories.return_value = ["mercado", "lazer"]
    service.get_income_categories.return_value = ["salario", "pix"]
    service.get_payment_methods.return_value = ["itau", "nubank"]
    return service


@pytest.fixture
def mock_graph_service():
    return AsyncMock(spec=GraphService)


@pytest.mark.asyncio
async def test_get_system_prompt_includes_income_categories(
    mock_llm, mock_finance_service, mock_graph_service
):
    agent_service = AgentService(
        llm=mock_llm,
        finance_service=mock_finance_service,
        graph_service=mock_graph_service,
    )

    prompt = await agent_service.get_system_prompt(platform="telegram")

    assert "'salario'" in prompt
    assert "'pix'" in prompt
    assert "CATEGORIAS DE RECEITAS VÁLIDAS" in prompt
    assert "Registro de Receitas" in prompt
    assert "Balanço Mensal" in prompt
