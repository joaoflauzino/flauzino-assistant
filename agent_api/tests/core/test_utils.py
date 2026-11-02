"""Unit tests for the token accounting and LLM observability helpers."""

import logging

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, Generation, LLMResult

from agent_api.core.metrics import (
    LLM_REQUEST_DURATION_SECONDS,
    LLM_REQUESTS_TOTAL,
    LLM_TOKENS_TOTAL,
)
from agent_api.core.schemas import TokenUsage
from agent_api.core.utils import (
    extract_token_usage,
    log_llm_end,
    record_llm_metrics,
    usage_from_generations,
    usage_from_mapping,
)


def result_with_llm_output(llm_output: dict | None) -> LLMResult:
    return LLMResult(generations=[[Generation(text="resposta")]], llm_output=llm_output)


def result_with_usage_metadata(prompt: int, completion: int) -> LLMResult:
    message = AIMessage(
        content="resposta",
        usage_metadata={
            "input_tokens": prompt,
            "output_tokens": completion,
            "total_tokens": prompt + completion,
        },
    )
    return LLMResult(generations=[[ChatGeneration(text="resposta", message=message)]])


def test_usage_from_mapping_reads_openai_token_usage():
    response = result_with_llm_output(
        {"token_usage": {"prompt_tokens": 15, "completion_tokens": 25}}
    )

    assert usage_from_mapping(response) == TokenUsage(prompt=15, completion=25)


def test_usage_from_mapping_accepts_input_and_output_keys():
    response = result_with_llm_output({"usage": {"input_tokens": 7, "output_tokens": 3}})

    assert usage_from_mapping(response) == TokenUsage(prompt=7, completion=3)


def test_usage_from_mapping_returns_zeroes_without_a_usage_mapping():
    assert usage_from_mapping(result_with_llm_output(None)) == TokenUsage()
    assert usage_from_mapping(result_with_llm_output({"token_usage": "n/a"})) == TokenUsage()


def test_usage_from_generations_sums_the_message_metadata():
    response = result_with_usage_metadata(prompt=11, completion=5)

    assert usage_from_generations(response) == TokenUsage(prompt=11, completion=5)


def test_usage_from_generations_ignores_generations_without_metadata():
    response = LLMResult(generations=[[Generation(text="sem metadata")]])

    assert usage_from_generations(response) == TokenUsage()


def test_extract_token_usage_prefers_the_llm_output_mapping():
    response = result_with_llm_output({"token_usage": {"prompt_tokens": 2, "completion_tokens": 4}})

    assert extract_token_usage(response) == TokenUsage(prompt=2, completion=4)


def test_extract_token_usage_falls_back_to_the_message_metadata():
    response = result_with_usage_metadata(prompt=9, completion=6)

    assert extract_token_usage(response) == TokenUsage(prompt=9, completion=6)


def test_extract_token_usage_returns_zeroes_when_the_provider_reports_nothing():
    assert extract_token_usage(result_with_llm_output(None)) == TokenUsage()


def test_record_llm_metrics_increments_requests_and_tokens():
    model = "gpt-4o-mini"
    requests_before = LLM_REQUESTS_TOTAL.labels(model=model, status="success")._value.get()
    prompt_before = LLM_TOKENS_TOTAL.labels(model=model, type="prompt")._value.get()
    completion_before = LLM_TOKENS_TOTAL.labels(model=model, type="completion")._value.get()

    record_llm_metrics(model, 1.5, TokenUsage(prompt=10, completion=20))

    assert (
        LLM_REQUESTS_TOTAL.labels(model=model, status="success")._value.get() == requests_before + 1
    )
    assert LLM_TOKENS_TOTAL.labels(model=model, type="prompt")._value.get() == prompt_before + 10
    assert (
        LLM_TOKENS_TOTAL.labels(model=model, type="completion")._value.get()
        == completion_before + 20
    )


def test_record_llm_metrics_still_observes_the_duration_without_tokens():
    model = "gpt-4o-mini"
    duration = LLM_REQUEST_DURATION_SECONDS.labels(model=model)
    sum_before = duration._sum.get()

    record_llm_metrics(model, 0.5, TokenUsage())

    assert duration._sum.get() == pytest.approx(sum_before + 0.5)


def test_log_llm_end_reports_the_token_split(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO, logger="agent_api.core.utils"):
        log_llm_end("1.20s", TokenUsage(prompt=3, completion=4))

    assert "1.20s" in caplog.text
    assert "3 prompt + 4 completion" in caplog.text
