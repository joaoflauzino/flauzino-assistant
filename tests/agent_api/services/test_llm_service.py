from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_api.schemas.assistant import AssistantResponse
from agent_api.services.llm import SYSTEM_PROMPT, get_llm_response


@pytest.mark.asyncio
async def test_get_llm_response_success(mocker):
    """
    Test that get_llm_response correctly calls the LLM with the right prompt and history.
    """
    # Arrange
    # Mock the entire LangChain invocation chain
    mock_llm_instance = MagicMock()
    mock_structured_output = MagicMock()
    mock_structured_output.ainvoke = AsyncMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_output

    # Patch the class to return our mocked instance
    mocker.patch(
        "agent_api.services.llm.ChatGoogleGenerativeAI", return_value=mock_llm_instance
    )

    # This is what we expect the LLM to return
    mock_assistant_response = AssistantResponse(
        response_message="Dados recebidos com sucesso!",
        spending_details=None,
        limit_details=None,
        is_complete=True,
    )
    mock_structured_output.ainvoke.return_value = mock_assistant_response

    sample_history = [
        {"role": "user", "content": "Olá"},
        {"role": "assistant", "content": "Olá, como posso ajudar?"},
    ]

    # Act
    result = await get_llm_response(sample_history)

    # Assert
    # Check that the LLM was initialized correctly
    mock_llm_instance.with_structured_output.assert_called_once_with(AssistantResponse)

    # Check that the final `ainvoke` was called
    mock_structured_output.ainvoke.assert_awaited_once()

    # Verify the messages passed to the LLM
    call_args = mock_structured_output.ainvoke.call_args[0][0]
    assert call_args[0] == ("system", SYSTEM_PROMPT)
    assert call_args[1] == ("human", "Olá")
    assert call_args[2] == ("ai", "Olá, como posso ajudar?")

    # Check that the result is what we mocked
    assert result == mock_assistant_response
