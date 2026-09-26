import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks.base import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from agent_api.core.logger import get_logger
from agent_api.core.metrics import (
    AGENT_TOOL_DURATION_SECONDS,
    AGENT_TOOL_EXECUTIONS_TOTAL,
    LLM_REQUEST_DURATION_SECONDS,
    LLM_REQUESTS_TOTAL,
    LLM_TOKENS_TOTAL,
)

logger = get_logger(__name__)


class AgentLoggingCallbackHandler(AsyncCallbackHandler):
    """Callback handler to log LLM and Tool executions with timing and arguments, and record Prometheus metrics."""

    def __init__(self) -> None:
        super().__init__()
        self._tool_info: dict[UUID, dict[str, Any]] = {}
        self._llm_info: dict[UUID, dict[str, Any]] = {}

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        model_name = (metadata or {}).get("ls_model_name") or serialized.get("name") or "LLM"
        self._llm_info[run_id] = {
            "start_time": time.perf_counter(),
            "model": model_name,
        }
        logger.info(f"🤖 [AGENT:LLM_START] Enviando requisição para o LLM ({model_name})...")

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        info = self._llm_info.pop(run_id, None)
        if info:
            elapsed_sec = time.perf_counter() - info["start_time"]
            model = info["model"]
            elapsed = f"{elapsed_sec:.2f}s"

            # Prometheus metrics
            LLM_REQUESTS_TOTAL.labels(model=model, status="success").inc()
            LLM_REQUEST_DURATION_SECONDS.labels(model=model).observe(elapsed_sec)

            # Extract token usage if available
            prompt_tokens = 0
            completion_tokens = 0

            if response.llm_output:
                usage = response.llm_output.get("token_usage") or response.llm_output.get("usage")
                if isinstance(usage, dict):
                    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                    completion_tokens = (
                        usage.get("completion_tokens") or usage.get("output_tokens") or 0
                    )

            if not (prompt_tokens or completion_tokens):
                for gen_list in response.generations:
                    for gen in gen_list:
                        msg = getattr(gen, "message", None)
                        if (
                            msg
                            and hasattr(msg, "usage_metadata")
                            and isinstance(msg.usage_metadata, dict)
                        ):
                            prompt_tokens += msg.usage_metadata.get("input_tokens", 0)
                            completion_tokens += msg.usage_metadata.get("output_tokens", 0)

            if prompt_tokens:
                LLM_TOKENS_TOTAL.labels(model=model, type="prompt").inc(prompt_tokens)
            if completion_tokens:
                LLM_TOKENS_TOTAL.labels(model=model, type="completion").inc(completion_tokens)

            logger.info(
                f"🤖 [AGENT:LLM_END] Resposta recebida do LLM em {elapsed}. "
                f"Tokens: {prompt_tokens} prompt + {completion_tokens} completion."
            )
        else:
            logger.info("🤖 [AGENT:LLM_END] Resposta recebida do LLM.")

    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        info = self._llm_info.pop(run_id, None)
        if info:
            elapsed_sec = time.perf_counter() - info["start_time"]
            model = info["model"]
            LLM_REQUESTS_TOTAL.labels(model=model, status="error").inc()
            LLM_REQUEST_DURATION_SECONDS.labels(model=model).observe(elapsed_sec)
            elapsed = f"{elapsed_sec:.2f}s"
        else:
            elapsed = "N/A"
        logger.error(f"❌ [AGENT:LLM_ERROR] Erro na chamada do LLM após {elapsed}: {error}")

    async def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name") or "tool"
        self._tool_info[run_id] = {
            "start_time": time.perf_counter(),
            "tool": tool_name,
        }
        args_repr = inputs if inputs is not None else input_str
        logger.info(
            f"🔧 [AGENT:TOOL_START] Executando tool '{tool_name}' com argumentos: {args_repr}"
        )

    async def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        info = self._tool_info.pop(run_id, None)
        if info:
            elapsed_sec = time.perf_counter() - info["start_time"]
            tool_name = info["tool"]
            AGENT_TOOL_EXECUTIONS_TOTAL.labels(tool=tool_name, status="success").inc()
            AGENT_TOOL_DURATION_SECONDS.labels(tool=tool_name).observe(elapsed_sec)
            elapsed = f"{elapsed_sec:.2f}s"
        else:
            elapsed = "N/A"

        # Truncate large outputs like charts/images for readable logs
        output_str = str(output)
        if len(output_str) > 250:
            output_str = output_str[:250] + "... [truncado]"
        logger.info(f"✅ [AGENT:TOOL_END] Tool concluída em {elapsed} com resultado: {output_str}")

    async def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        info = self._tool_info.pop(run_id, None)
        if info:
            elapsed_sec = time.perf_counter() - info["start_time"]
            tool_name = info["tool"]
            AGENT_TOOL_EXECUTIONS_TOTAL.labels(tool=tool_name, status="error").inc()
            AGENT_TOOL_DURATION_SECONDS.labels(tool=tool_name).observe(elapsed_sec)
            elapsed = f"{elapsed_sec:.2f}s"
        else:
            elapsed = "N/A"
        logger.error(f"❌ [AGENT:TOOL_ERROR] Falha na execução da tool após {elapsed}: {error}")
