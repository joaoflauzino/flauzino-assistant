import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks.base import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

from agent_api.core.logger import get_logger

logger = get_logger(__name__)


class AgentLoggingCallbackHandler(AsyncCallbackHandler):
    """Callback handler to log LLM and Tool executions with timing and arguments."""

    def __init__(self) -> None:
        super().__init__()
        self._tool_start_times: dict[UUID, float] = {}
        self._llm_start_times: dict[UUID, float] = {}

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
        self._llm_start_times[run_id] = time.perf_counter()
        model_name = (metadata or {}).get("ls_model_name") or serialized.get("name") or "LLM"
        logger.info(f"🤖 [AGENT:LLM_START] Enviando requisição para o LLM ({model_name})...")

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        start_time = self._llm_start_times.pop(run_id, None)
        elapsed = f"{time.perf_counter() - start_time:.2f}s" if start_time else "N/A"
        logger.info(f"🤖 [AGENT:LLM_END] Resposta recebida do LLM em {elapsed}.")

    async def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        start_time = self._llm_start_times.pop(run_id, None)
        elapsed = f"{time.perf_counter() - start_time:.2f}s" if start_time else "N/A"
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
        self._tool_start_times[run_id] = time.perf_counter()
        tool_name = serialized.get("name") or "tool"
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
        start_time = self._tool_start_times.pop(run_id, None)
        elapsed = f"{time.perf_counter() - start_time:.2f}s" if start_time else "N/A"
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
        start_time = self._tool_start_times.pop(run_id, None)
        elapsed = f"{time.perf_counter() - start_time:.2f}s" if start_time else "N/A"
        logger.error(f"❌ [AGENT:TOOL_ERROR] Falha na execução da tool após {elapsed}: {error}")
