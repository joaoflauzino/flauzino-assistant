# Walkthrough: Tools Nativas no `agent_api`, `graph_api` REST e MCP na `finance_api`

Finalizamos com sucesso a migração arquitetural do ecossistema do Flauzino Assistant, eliminando a complexidade acidental do protocolo MCP no fluxo interno entre microsserviços e centralizando o MCP na `finance_api` como ponto único de entrada para agentes de desktop (Claude Desktop, Cursor, etc.).

---

## Resumo das Mudanças

### 1. `graph_api` (ex-`mcp_server`): Função Pura de Plotagem via REST
- **Renomeação:** Diretório renomeado de `mcp_server` para `graph_api`.
- **Desacoplamento:** Removida a dependência de rede com a `finance_api` (`finance_service.py` excluído). A API não busca dados no banco e não conhece a `finance_api`.
- **Eliminação de MCP interno:** Removido o servidor FastMCP e a dependência da SDK `mcp`. O serviço agora é 100% FastAPI REST puro.
- **Endpoints REST (`graph_api/routers/graphs.py`):**
  - `POST /graphs/bar`: Recebe `BalanceBarChartRequest` (`balances: list[CategoryBalanceItem]`, `mode`, `title`) e devolve `GraphImageResponse` com imagem PNG Base64.
  - `POST /graphs/pie`: Recebe `ExpensePieChartRequest` (`balances: list[CategoryBalanceItem]`, `title`) e devolve `GraphImageResponse`.
- **Testes dedicados:** Criado `graph_api/tests/test_graphs_router.py` (3 testes cobrindo rotas e tratamento de erros).

### 2. `agent_api`: Orquestração Determinística com Tools Nativas
- **Remoção do cliente MCP em rede:** Excluído `agent_api/services/mcp_client.py` e removida a dependência do pacote `mcp`.
- **Novo `GraphService` (`agent_api/services/graph.py`):** Cliente HTTP direto que consome a `graph_api` via REST (`POST /graphs/bar`, `POST /graphs/pie`).
- **Orquestração determinística no `ChatService` (`agent_api/services/chat.py`):**
  - Quando a LLM solicita gráfico (`requested_graph_type`), o `chat.py` busca os saldos na `finance_api` via HTTP interno.
  - Envia os dados estruturados diretamente para a `graph_api`.
  - Anexa o Base64 à resposta do usuário sem sobrecarga de handshake de protocolo ou timeout.
- **System Prompt limpo (`agent_api/services/llm.py`):** As ferramentas de gráficos suportadas são definidas diretamente sem necessidade de polling/cache de rede via MCP.

### 3. `finance_api`: Servidor MCP Oficial para Agentes de Desktop
- **Nova interface MCP (`finance_api/mcp/`):**
  - `server.py`: Servidor singleton `FastMCP("flauzino-finance", host="0.0.0.0")` montado no endpoint `/mcp` via Streamable HTTP.
  - `MCPStreamableApp`: Adaptador ASGI com suporte a recriação limpa de `StreamableHTTPSessionManager` a cada `lifespan` (compatível com múltiplos testes simultâneos).
- **Tools expostas para Claude Desktop / Cursor (`finance_api/mcp/tools.py`):**
  - `get_category_balance`: Retorna saldo, limite, gastos e percentual de cada categoria.
  - `create_spent`: Registra novo gasto no banco de dados.
  - `list_categories`: Lista todas as categorias disponíveis.
  - `get_balance_chart`: Consulta os saldos locais, consome a `graph_api` via REST e retorna o gráfico formatado como `Image(data=..., format="png")` direto para o chat do desktop!
- **Testes automatizados:** Criado `tests/finance_api/test_mcp_tools.py` (5 testes validando listagem e chamada das tools).

### 4. Integração do Ecossistema (`telegram_api`, `infra`, `scripts`, `Makefile`)
- **`telegram_api`:** Atualizado `balance_handler.py` e rotina semanal no `main.py` para consultar saldos na `finance_api` e gerar gráficos via `POST` na `graph_api`.
- **`Makefile`:** Adicionados comandos `make run-graph` e `make test-graph`.
- **`infra/docker-compose.yml` e `graph_api/Dockerfile`:** Atualizados para o serviço `graph_api` e novas variáveis `GRAPH_SERVICE_URL`.
- **`scripts/test_mcp_isolated.py`:** Atualizado para testar o endpoint `http://localhost:8000/mcp` da `finance_api`.

---

## Verificação e Testes

### 1. Testes Automatizados
Todos os testes do repositório foram executados com sucesso:
- **`graph_api`**: 3 testes passando (`pytest graph_api/tests`)
- **`finance_api`**: 40 testes passando (`pytest tests/finance_api/`)
- **`agent_api`**: 53 testes passando (`pytest tests/agent_api/`)
- **`telegram_api` & integração**: 27 testes passando
- **Total: 123 testes passando sem falhas.**

```bash
$ pytest
======================= 120 passed, 3 warnings in 1.66s ========================

$ pytest graph_api/tests
======================== 3 passed, 14 warnings in 1.14s ========================
```

### 2. Formatação e Linter (PEP 8)
```bash
$ black --check . && ruff check .
All done! ✨ 🍰 ✨
141 files would be left unchanged.
All checks passed!
```
