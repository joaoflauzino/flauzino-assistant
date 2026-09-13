# Especificação: Refatoração Arquitetural do MCP Server

Esta especificação documenta a arquitetura do `mcp_server`, que originalmente era um monolito de ~267 linhas em `main.py`, refatorado para uma arquitetura em camadas alinhada com as diretrizes do `GEMINI.md`.

## 1. Visão Geral

O `mcp_server` é um serviço independente (Docker container) responsável por:
- Gerar gráficos financeiros (barras e pizza) com Plotly/Kaleido.
- Expor esses gráficos como **MCP Tools** via transporte **Streamable HTTP** (endpoint `/mcp`) para consumo pelo agente LLM.
- Expor um endpoint REST (`/graphs/balance`) para consumo direto pelo bot do Telegram.

**Problema original:** Todo o código (configuração, lógica de negócio, geração de gráficos, rotas HTTP, protocolo MCP) estava concentrado em um único `main.py`, violando múltiplas diretrizes do projeto:
1. Variável `FINANCE_SERVICE_URL` forçada via `os.getenv` no topo do arquivo.
2. Rotas, lógica de negócio e geração de gráficos misturados no mesmo módulo.
3. `try/except Exception` genéricos em vez de exceções customizadas + handlers globais.
4. Endpoints sem `response_model`, sem `Query()` com tipagem — descumprindo boas práticas FastAPI.

**Refatoração de protocolo (2026-08):** o transporte **SSE** (deprecado no spec do MCP) e o low-level `Server` foram substituídos por **`FastMCP` + Streamable HTTP**, e o consumo no `agent_api` passou a usar um **cliente MCP HTTP** com descoberta dinâmica de tools via `tools/list`.

---

## 2. Arquitetura

```
mcp_server/
├── core/
│   ├── __init__.py
│   ├── settings.py        ← pydantic-settings (FINANCE_SERVICE_URL)
│   ├── exceptions.py      ← MCPServerError, FinanceClientError, GraphGenerationError, ServiceError
│   ├── handlers.py        ← Global exception handlers (FastAPI)
│   ├── decorators.py      ← @handle_service_errors
│   └── mcp.py             ← Instância singleton do FastMCP("graph-generator")
├── schemas/
│   ├── __init__.py
│   └── graphs.py          ← GraphImageResponse (Pydantic BaseModel)
├── services/
│   ├── __init__.py
│   ├── finance_service.py ← fetch_balance() — client HTTP para finance_api
│   ├── graph_service.py   ← generate_balance_bar_chart(), generate_expense_pie_chart()
│   └── mcp_service.py     ← @mcp.tool() — registra as MCP Tools
├── routers/
│   ├── __init__.py
│   └── graphs.py          ← GET /graphs/balance (REST)
├── tests/
│   ├── conftest.py        ← Adiciona a raiz do projeto ao sys.path
│   ├── test_mcp_protocol.py ← Testes in-memory do protocolo (tools/list, tools/call)
│   └── test_mcp_http.py   ← Teste de integração via HTTP real (uvicorn subprocesso)
├── main.py                ← Entrypoint enxuto (~45 linhas)
├── Dockerfile
└── pyproject.toml
```

---

## 3. Detalhamento das Camadas

### 3.1. Core (`core/`)

#### `settings.py`
```python
class MCPServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    FINANCE_SERVICE_URL: str = "http://finance_api:8000"
```

#### `exceptions.py`
Hierarquia de exceções customizadas:
- `MCPServerError` (base)
  - `FinanceClientError` — falha na comunicação com o `finance_api`
  - `GraphGenerationError` — falha na renderização de gráficos (Plotly/Kaleido)
  - `ServiceError` — erros genéricos internos do serviço

#### `handlers.py`
Handlers globais do FastAPI, mapeando cada exceção para status HTTP:
- `FinanceClientError` → 502 Bad Gateway
- `GraphGenerationError` → 500
- `ServiceError` → 500
- `MCPServerError` → 500 (catch-all)

#### `decorators.py`
```python
@handle_service_errors  # Captura httpx.HTTPStatusError, httpx.RequestError, e Exception genérica
```

#### `mcp.py`
```python
mcp = FastMCP(
    "graph-generator",
    host="0.0.0.0",  # evita a proteção anti DNS-rebinding (bloquearia agent_api -> mcp_server:8002)
)
```
Instância singleton do **`FastMCP`** (API moderna do MCP). O `host` não-localhost evita que o FastMCP ative a proteção anti DNS-rebinding, que rejeitaria requisições vindas de outros serviços na rede Docker.

### 3.2. Services (`services/`)

#### `finance_service.py`
- Extrai a função `fetch_balance()` do `main.py` original.
- Usa `settings.FINANCE_SERVICE_URL` em vez de `os.getenv`.
- Decorada com `@handle_service_errors`.

#### `graph_service.py`
- Extrai `generate_balance_bar_chart()` e `generate_expense_pie_chart()`.
- Erros de renderização Plotly são capturados e convertidos em `GraphGenerationError`.
- Decoradas com `@handle_service_errors`.

#### `mcp_service.py`
- Registra as MCP Tools com decorators **`@mcp.tool()`** do FastMCP:
  - `plot_category_balance(reference_month, categories, mode)` — barras comparando limites vs gastos.
  - `plot_expense_pie_chart(reference_month, categories)` — pizza com distribuição de gastos.
- Schemas de entrada são gerados automaticamente de type hints + `Annotated[..., Field(description=...)]`.
- Retornam `Image` (→ `ImageContent` base64) ou `str` (→ `TextContent`).
- Delegam para `finance_service` e `graph_service`. Sem `try/except` — erros propagam como exceções de domínio.

### 3.3. Routers (`routers/`)

#### `graphs.py`
- `GET /graphs/balance` com `response_model=GraphImageResponse`.
- Parâmetros tipados com `Query()` e descrições.
- Zero lógica de negócio — delega para os services.

### 3.4. Main (`main.py`)
- ~45 linhas.
- Cria o `StreamableHTTPSessionManager` (com `mcp._mcp_server`) e o `StreamableHTTPASGIApp`.
- No **lifespan** do FastAPI roda `session_manager.run()` — o task group do transporte é criado lá (requisito do manager; o app retornado por `streamable_http_app()` não roda seu próprio lifespan quando montado).
- Monta o transporte em `app.mount("/mcp", streamable_http_app)`.
- Registra exception handlers, routers, e importa `services.mcp_service` para trigger dos decorators de registro de tools.

### 3.5. Testes (`tests/`)

- **`test_mcp_protocol.py`** — testes in-memory (via `mcp.shared.memory`) do protocolo MCP com `finance_service` mockado: `tools/list` descobre as tools, `tools/call` gera PNG válido (bytes `\x89PNG`), e responde com texto quando não há dados.
- **`test_mcp_http.py`** — sobe o servidor real (uvicorn em subprocesso na porta livre) e faz o fluxo completo via HTTP: `initialize` → `tools/list`.
- Rodam com o venv unificado do workspace (deps plotly/kaleido instaladas na raiz):
  ```bash
  uv sync --all-packages   # instala deps de todos os serviços + dev no .venv raiz
  uv run pytest mcp_server/tests
  ```
  O `testpaths` da raiz (`tests`) exclui `mcp_server/tests` por padrão; passá-lo como argumento roda só os testes do MCP.

---

## 4. Cliente MCP no agent_api

O `agent_api` consome o MCP server via HTTP (Streamable HTTP) em `services/mcp_client.py`:
- `list_tools()` — descoberta real das tools via `tools/list`.
- `call_tool(name, arguments)` — retorna `MCPServerResult` com `image_base64`, `text` e `is_error`.
- A URL é `{MCP_SERVER_URL}/mcp` (padrão `http://localhost:8002/mcp`).

Integração:
- `services/chat.py` usa `mcp_client.call_tool()` quando a LLM sinaliza `requested_graph_type` (substitui o bloco inline de `sse_client`).
- `services/llm.py` monta a seção "FERRAMENTAS DE GRÁFICO DISPONÍVEIS" do system prompt **dinamicamente** a partir de `get_mcp_tools_summary()` (cache de 60s + fallback estático se o MCP estiver offline). Nenhum nome de tool fica hardcoded.
- Script de verificação manual ponta a ponta: `scripts/test_mcp_isolated.py`.

---

## 5. Decisões Técnicas

| Decisão | Justificativa |
|---|---|
| **FastMCP + Streamable HTTP** em vez de low-level `Server` + SSE | Transporte SSE foi deprecado no spec MCP; Streamable HTTP é o padrão atual (POST/GET/DELETE, HTTP de verdade). FastMCP gera schemas automaticamente e é a API recomendada. |
| `host="0.0.0.0"` no FastMCP | Impede que o FastMCP ative a proteção anti DNS-rebinding (que rejeitaria `agent_api -> mcp_server:8002` na rede Docker). |
| `StreamableHTTPSessionManager` integrado ao lifespan do FastAPI | `streamable_http_app()` retorna um app Starlette cujo lifespan não roda quando montado em outro app; integrar o manager no lifespan do FastAPI é o padrão documentado. |
| Imports `mcp_server.*` (pacote completo) | O serviço roda como pacote `mcp_server` (namespace package) dentro da rede Docker (`uvicorn mcp_server.main:app`), consistente com o Dockerfile. |
| **Workspace uv unificado (2026-08)** | Cada serviço virou membro do workspace com `pyproject.toml` próprio e `[tool.uv] package = false`. Dev usa um único `.venv` na raiz (`uv sync --all-packages`); Docker usa `uv sync --frozen --no-dev --package <serviço>` para instalar só as deps do serviço (imagens slim). Um único `uv.lock` na raiz. |
| `mcp_service.py` como serviço (não router) | As tools MCP são lógica de orquestração (chamam finance_service e graph_service), não endpoints HTTP diretos. O padrão `route -> service` se mantém. |
| Descoberta dinâmica de tools no agent_api | O prompt da LLM é construído a partir de `tools/list` (com cache/fallback). Adicionar tool nova no MCP não exige editar prompt. |

---

## 6. Status
- **Implementada:** ✅ (30/07/2026)
- **Refatoração protocolo (Streamable HTTP + FastMCP + client HTTP):** ✅ (13/08/2026)
- **Workspace uv unificado (1 venv na raiz):** ✅ (13/08/2026)
- **Validada:** ✅ Imports, OpenAPI, 115 testes da raiz + 6 testes do MCP server, ruff/black limpos, teste ponta a ponta real via `scripts/test_mcp_isolated.py`.
