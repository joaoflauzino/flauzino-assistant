"""Token accounting and LLM observability helpers shared by the agent core."""

from langchain_core.outputs import LLMResult

from agent_api.core.logger import get_logger
from agent_api.core.metrics import (
    LLM_REQUEST_DURATION_SECONDS,
    LLM_REQUESTS_TOTAL,
    LLM_TOKENS_TOTAL,
)
from agent_api.core.schemas import TokenUsage

logger = get_logger(__name__)


def usage_from_mapping(response: LLMResult) -> TokenUsage:
    """Reads token usage from the provider's ``llm_output`` mapping."""
    llm_output = response.llm_output or {}
    usage = llm_output.get("token_usage") or llm_output.get("usage")
    if not isinstance(usage, dict):
        return TokenUsage()
    return TokenUsage(
        prompt=usage.get("prompt_tokens") or usage.get("input_tokens") or 0,
        completion=usage.get("completion_tokens") or usage.get("output_tokens") or 0,
    )


def usage_from_generations(response: LLMResult) -> TokenUsage:
    """Sums the usage metadata attached to each generated message."""
    usage = TokenUsage()
    for generation_list in response.generations:
        for generation in generation_list:
            message = getattr(generation, "message", None)
            metadata = getattr(message, "usage_metadata", None)
            if not isinstance(metadata, dict):
                continue
            usage.prompt += metadata.get("input_tokens", 0)
            usage.completion += metadata.get("output_tokens", 0)
    return usage


def extract_token_usage(response: LLMResult) -> TokenUsage:
    """Read token usage from the LLM output, falling back to per-message metadata."""
    usage = usage_from_mapping(response)
    if usage.prompt or usage.completion:
        return usage
    return usage_from_generations(response)


def record_llm_metrics(model: str, elapsed_sec: float, usage: TokenUsage) -> None:
    """Records a successful LLM call and its token consumption."""
    LLM_REQUESTS_TOTAL.labels(model=model, status="success").inc()
    LLM_REQUEST_DURATION_SECONDS.labels(model=model).observe(elapsed_sec)
    if usage.prompt:
        LLM_TOKENS_TOTAL.labels(model=model, type="prompt").inc(usage.prompt)
    if usage.completion:
        LLM_TOKENS_TOTAL.labels(model=model, type="completion").inc(usage.completion)


def log_llm_end(elapsed: str, usage: TokenUsage) -> None:
    """Logs the completed LLM call with its timing and token split."""
    logger.info(
        f"🤖 [AGENT:LLM_END] Resposta recebida do LLM em {elapsed}. "
        f"Tokens: {usage.prompt} prompt + {usage.completion} completion."
    )
