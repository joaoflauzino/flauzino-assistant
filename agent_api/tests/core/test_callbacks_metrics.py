import pytest
from uuid import uuid4
from langchain_core.outputs import LLMResult, Generation

from agent_api.core.callbacks import AgentLoggingCallbackHandler
from agent_api.core.metrics import (
    LLM_REQUESTS_TOTAL,
    LLM_TOKENS_TOTAL,
    AGENT_TOOL_EXECUTIONS_TOTAL,
)


@pytest.mark.asyncio
async def test_callback_records_llm_metrics_and_tokens():
    handler = AgentLoggingCallbackHandler()
    run_id = uuid4()
    model = "gpt-4o-mini"

    # Start LLM
    await handler.on_llm_start(
        serialized={"name": model},
        prompts=["Ola mundo"],
        run_id=run_id,
        metadata={"ls_model_name": model},
    )

    # End LLM with tokens in llm_output
    result = LLMResult(
        generations=[[Generation(text="Resposta do modelo")]],
        llm_output={
            "token_usage": {
                "prompt_tokens": 15,
                "completion_tokens": 25,
                "total_tokens": 40,
            }
        },
    )

    prompt_before = LLM_TOKENS_TOTAL.labels(model=model, type="prompt")._value.get()
    completion_before = LLM_TOKENS_TOTAL.labels(model=model, type="completion")._value.get()
    success_calls_before = LLM_REQUESTS_TOTAL.labels(model=model, status="success")._value.get()

    await handler.on_llm_end(result, run_id=run_id)

    prompt_after = LLM_TOKENS_TOTAL.labels(model=model, type="prompt")._value.get()
    completion_after = LLM_TOKENS_TOTAL.labels(model=model, type="completion")._value.get()
    success_calls_after = LLM_REQUESTS_TOTAL.labels(model=model, status="success")._value.get()

    assert prompt_after == prompt_before + 15
    assert completion_after == completion_before + 25
    assert success_calls_after == success_calls_before + 1


@pytest.mark.asyncio
async def test_callback_records_tool_metrics():
    handler = AgentLoggingCallbackHandler()
    run_id = uuid4()
    tool_name = "get_expenses"

    await handler.on_tool_start(
        serialized={"name": tool_name},
        input_str='{"month": 3}',
        run_id=run_id,
    )

    success_before = AGENT_TOOL_EXECUTIONS_TOTAL.labels(
        tool=tool_name, status="success"
    )._value.get()
    await handler.on_tool_end(output="gastos encontrados: R$ 50", run_id=run_id)
    success_after = AGENT_TOOL_EXECUTIONS_TOTAL.labels(
        tool=tool_name, status="success"
    )._value.get()

    assert success_after == success_before + 1


@pytest.mark.asyncio
async def test_callback_records_llm_error():
    handler = AgentLoggingCallbackHandler()
    run_id = uuid4()
    model = "gpt-4o-mini"

    await handler.on_llm_start(
        serialized={"name": model},
        prompts=["Ola"],
        run_id=run_id,
        metadata={"ls_model_name": model},
    )

    error_before = LLM_REQUESTS_TOTAL.labels(model=model, status="error")._value.get()
    await handler.on_llm_error(error=RuntimeError("Timeout"), run_id=run_id)
    error_after = LLM_REQUESTS_TOTAL.labels(model=model, status="error")._value.get()

    assert error_after == error_before + 1
