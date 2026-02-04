from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.exceptions import OutputParserException
from google.api_core.exceptions import GoogleAPIError

from agent_api.schemas.assistant import AssistantResponse
from agent_api.services.llm import get_llm_response
from agent_api.core.exceptions import LLMParsingError, LLMProviderError


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
    # First message should be system prompt (dynamically generated)
    assert call_args[0][0] == "system"
    assert len(call_args[0][1]) > 0  # Should have content
    assert call_args[1] == ("human", "Olá")
    assert call_args[2] == ("ai", "Olá, como posso ajudar?")

    # Check that the result is what we mocked
    assert result == mock_assistant_response


@pytest.mark.asyncio
async def test_get_llm_response_parsing_error(mocker):
    """Test that OutputParserException is caught and raised as LLMParsingError."""
    # Arrange
    mock_llm_instance = MagicMock()
    mock_structured_output = MagicMock()
    mock_structured_output.ainvoke = AsyncMock(
        side_effect=OutputParserException("Parsing failed")
    )
    mock_llm_instance.with_structured_output.return_value = mock_structured_output

    mocker.patch(
        "agent_api.services.llm.ChatGoogleGenerativeAI", return_value=mock_llm_instance
    )

    # Act & Assert
    with pytest.raises(LLMParsingError) as exc_info:
        await get_llm_response([])
    assert "Failed to parse LLM response" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_llm_response_google_api_error(mocker):
    """Test that GoogleAPIError is caught and raised as LLMProviderError."""
    # Arrange
    mock_llm_instance = MagicMock()
    mock_structured_output = MagicMock()
    mock_structured_output.ainvoke = AsyncMock(side_effect=GoogleAPIError("API Error"))
    mock_llm_instance.with_structured_output.return_value = mock_structured_output

    mocker.patch(
        "agent_api.services.llm.ChatGoogleGenerativeAI", return_value=mock_llm_instance
    )

    # Act & Assert
    with pytest.raises(LLMProviderError) as exc_info:
        await get_llm_response([])
    assert "Google Gemini Error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_llm_response_unknown_error(mocker):
    """Test that generic Exception is caught and raised as LLMUnknownError."""
    # Arrange
    mock_llm_instance = MagicMock()
    mock_structured_output = MagicMock()
    mock_structured_output.ainvoke = AsyncMock(side_effect=Exception("Unexpected boom"))
    mock_llm_instance.with_structured_output.return_value = mock_structured_output

    mocker.patch(
        "agent_api.services.llm.ChatGoogleGenerativeAI", return_value=mock_llm_instance
    )

    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await get_llm_response([])
    assert "Unexpected boom" in str(exc_info.value)
