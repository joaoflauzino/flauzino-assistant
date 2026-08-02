# Especificação: Refatoração Arquitetural do MCP Server

Esta especificação documenta o plano de refatoração do `mcp_server`, que originalmente era um monolito de ~267 linhas em `main.py`, para uma arquitetura em camadas alinhada com as diretrizes do `GEMINI.md`.

## 1. Visão Geral

O `mcp_server` é um serviço independente (Docker container) responsável por:
- Gerar gráficos financeiros (barras e pizza) com Plotly/Kaleido.
- Expor esses gráficos como **MCP Tools** (via protocolo SSE) para consumo pelo agente LLM.
- Expor um endpoint REST (`/graphs/balance`) para consumo direto pelo bot do Telegram.

**Problema:** Todo o código (configuração, lógica de negócio, geração de gráficos, rotas HTTP, protocolo MCP) estava concentrado em um único `main.py`, violando múltiplas diretrizes do projeto:
1. Variável `FINANCE_SERVICE_URL` forçada via `os.getenv` no topo do arquivo.
2. Rotas, lógica de negócio e geração de gráficos misturados no mesmo módulo.
3. `try/except Exception` genéricos em vez de exceções customizadas + handlers globais.
4. Endpoints sem `response_model`, sem `Query()` com tipagem — descumprindo boas práticas FastAPI.

---

## 2. Arquitetura Proposta

```
mcp_server/
├── core/
│   ├── __init__.py
│   ├── settings.py        ← pydantic-settings (FINANCE_SERVICE_URL)
│   ├── exceptions.py      ← MCPServerError, FinanceClientError, GraphGenerationError, ServiceError
│   ├── handlers.py        ← Global exception handlers (FastAPI)
│   ├── decorators.py      ← @handle_service_errors
│   └── mcp.py             ← Instância singleton do Server("graph-generator")
├── schemas/
│   ├── __init__.py
│   └── graphs.py          ← GraphImageResponse (Pydantic BaseModel)
├── services/
│   ├── __init__.py
│   ├── finance_service.py ← fetch_balance() — client HTTP para finance_api
│   ├── graph_service.py   ← generate_balance_bar_chart(), generate_expense_pie_chart()
│   └── mcp_service.py     ← @mcp_server.list_tools(), @mcp_server.call_tool()
├── routers/
│   ├── __init__.py
│   ├── graphs.py          ← GET /graphs/balance (REST)
│   └── mcp.py             ← GET /sse + SSE transport mount (protocolo MCP)
├── main.py                ← Entrypoint enxuto (~40 linhas)
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
- Registra as MCP Tools (`plot_category_balance`, `plot_expense_pie_chart`).
- Delega para `finance_service` e `graph_service`.
- Sem `try/except` — erros propagam como exceções de domínio.

### 3.3. Routers (`routers/`)

#### `graphs.py`
- `GET /graphs/balance` com `response_model=GraphImageResponse`.
- Parâmetros tipados com `Query()` e descrições.
- Zero lógica de negócio — delega para os services.

#### `mcp.py`
- Endpoint `/sse` para comunicação MCP.
- Expõe `get_sse_transport()` para montagem no `main.py`.

### 3.4. Main (`main.py`)
- ~40 linhas.
- Registra exception handlers, routers, e monta o SSE transport.
- Importa `services.mcp_service` para trigger dos decorators de registro de tools.

---

## 4. Decisões Técnicas

| Decisão | Justificativa |
|---|---|
| Imports flat (`core.*`, `services.*`) em vez de `mcp_server.core.*` | O serviço roda isolado em Docker com `WORKDIR /app`. Imports flat eliminam a necessidade de instalação como pacote Python e são consistentes com o Dockerfile original. |
| `.venv` separado por serviço | Cada serviço tem seu Dockerfile e `pyproject.toml`. O `mcp_server` usa deps pesadas (`plotly`, `kaleido`, `numpy`, `pandas`) que não devem poluir outros serviços. |
| `mcp_service.py` como serviço (não router) | As tools MCP são lógica de orquestração (chamam finance_service e graph_service), não endpoints HTTP diretos. O padrão `route -> service` se mantém. |

---

## 5. Status
- **Implementada:** ✅ (30/07/2026)
- **Validada:** ✅ Imports e rotas OpenAPI verificados
