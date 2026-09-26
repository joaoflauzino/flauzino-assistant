# Graph API

Microsserviço FastAPI especializado na geração e renderização de gráficos financeiros estáticos de alta resolução (PNG codificado em Base64), utilizando [Plotly](https://plotly.com/python/) e [Kaleido](https://github.com/plotly/Kaleido).

O serviço é consumido diretamente pelo **Telegram Bot** (para `/saldo`, `/limites` e relatório semanal) e pelas **MCP Tools da Finance API**.

---

## Endpoints

A documentação interativa OpenAPI/Swagger está disponível em `http://localhost:8002/docs`.

### 1. Gráfico de Barras — `POST /graphs/bar`

Gera um gráfico de barras comparativo (gastos vs. limites ou visão geral de limites cadastrados).

**Payload (`BalanceBarChartRequest`):**
```json
{
  "balances": [
    {
      "category_display_name": "Alimentação",
      "limit": 1500.0,
      "spent": 850.0,
      "available": 650.0
    },
    {
      "category_display_name": "Transporte",
      "limit": 500.0,
      "spent": 320.0,
      "available": 180.0
    }
  ],
  "title": "Saldo Atual e Gastos",
  "mode": "saldo"
}
```

> **Modos disponíveis:** `saldo` (compara limite vs. gasto realizado) e `limites` (exibe limites cadastrados).

**Resposta (`GraphImageResponse`):**
```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

---

### 2. Gráfico de Pizza — `POST /graphs/pie`

Gera um gráfico de pizza exibindo a distribuição percentual e absoluta de gastos por categoria.

**Payload (`ExpensePieChartRequest`):**
```json
{
  "balances": [
    {
      "category_display_name": "Alimentação",
      "spent": 850.0
    },
    {
      "category_display_name": "Transporte",
      "spent": 320.0
    },
    {
      "category_display_name": "Lazer",
      "spent": 210.0
    }
  ],
  "title": "Distribuição de Gastos por Categoria"
}
```

**Resposta (`GraphImageResponse`):**
```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

---

## Como Executar

### Localmente
```bash
make run-graph
# ou
uv run uvicorn graph_api.main:app --port 8002 --reload
```

A API estará acessível em `http://localhost:8002`.

### Docker
O serviço é executado como parte da stack no `infra/docker-compose.yml`:
```bash
docker-compose -f infra/docker-compose.yml up -d graph_api
```

---

## Testes

Para executar os testes unitários do serviço:
```bash
make test-graph
# ou
uv run pytest graph_api/tests
```
