from prometheus_client import Counter, Histogram

# LLM metrics
LLM_REQUESTS_TOTAL = Counter(
    "flauzino_llm_requests_total",
    "Total de chamadas realizadas ao modelo de LLM",
    ["model", "status"],
)

LLM_TOKENS_TOTAL = Counter(
    "flauzino_llm_tokens_total",
    "Total de tokens consumidos no LLM",
    ["model", "type"],  # "prompt" ou "completion"
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "flauzino_llm_request_duration_seconds",
    "Duração das requisições ao LLM em segundos",
    ["model"],
    buckets=[0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 30.0],
)

# Agent tools metrics
AGENT_TOOL_EXECUTIONS_TOTAL = Counter(
    "flauzino_agent_tool_executions_total",
    "Total de execuções de ferramentas (tools) pelo agente",
    ["tool", "status"],
)

AGENT_TOOL_DURATION_SECONDS = Histogram(
    "flauzino_agent_tool_duration_seconds",
    "Duração da execução de ferramentas (tools) em segundos",
    ["tool"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)
