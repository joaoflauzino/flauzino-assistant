# Infraestrutura & Configurações

Guia completo da infraestrutura do **Flauzino Assistant**, abrangendo a orquestração com Docker Compose, configuração do banco de dados relacional PostgreSQL, especificações de variáveis de ambiente e stack de observabilidade com Prometheus e Grafana.

---

## Topologia de Serviços

Toda a stack de microsserviços pode ser instanciada via contêineres gerenciados pelo Docker Compose (`infra/docker-compose.yml`), compartilhando uma rede interna (`default`):

| Serviço | Contêiner | Porta Exposta | Descrição |
|:---|:---|:---|:---|
| **db** | `postgres:17-alpine` | `5432:5432` | Banco de dados PostgreSQL com volume persistente e script de inicialização |
| **finance_api** | `flauzino-assistant/finance_api` | `8000:8000` | API central de regras de negócio, persistência, `/metrics` e MCP tools |
| **agent_api** | `flauzino-assistant/agent_api` | `8001:8001` | API inteligente com LLM, `/metrics` (incluindo tokens e tools) e OCR |
| **graph_api** | `flauzino-assistant/graph_api` | `8002:8002` | Microsserviço de renderização de gráficos com Plotly, Kaleido e `/metrics` |
| **frontend** | `flauzino-assistant/frontend` | `5173:80` | Interface Web SPA React servida através do Nginx |
| **telegram_bot** | `flauzino-assistant/telegram_bot` | `8003:8003` | Worker assíncrono do bot do Telegram com `/metrics` de mensagens |
| **prometheus** | `prom/prometheus:v2.54.1` | `9090:9090` | Servidor de métricas em séries temporais (coleta `/metrics` a cada 10s) |
| **grafana** | `grafana/grafana:11.2.0` | `3000:3000` | Painéis visuais interativos pré-provisionados com métricas e LLM |

---

## Comandos de Operação

### Executar Toda a Stack
Para construir as imagens e iniciar todos os serviços em segundo plano:
```bash
make docker-up
# ou: docker-compose --env-file .env -f infra/docker-compose.yml up -d --build
```

Para parar todos os contêineres:
```bash
make docker-down
# ou: docker-compose -f infra/docker-compose.yml down
```

### Executar Apenas o Banco de Dados (Desenvolvimento Local)
Se você for executar as APIs ou o frontend diretamente na sua máquina hospedeira:
```bash
make db-up
# ou: docker-compose --env-file .env -f infra/docker-compose.yml up -d db
```

Para parar o banco de dados:
```bash
make db-down
```

> **Aviso para macOS (Apple Silicon):**
> O serviço de banco especifica `platform: linux/arm64`. Caso use outra arquitetura, defina a variável `ARCH` se necessário.

### Logs dos Serviços
Para visualizar e acompanhar os logs em tempo real:
```bash
# Todos os serviços:
docker-compose -f infra/docker-compose.yml logs -f

# Apenas um serviço específico (ex: agent_api):
docker-compose -f infra/docker-compose.yml logs -f agent_api
```

---

## Observabilidade (Prometheus + Grafana)

A stack conta com monitoramento em tempo real de saúde, taxa de chamadas, latência, erros HTTP, consumo de LLMs e bot do Telegram:

### Acessos
- **Grafana**: [http://localhost:3000](http://localhost:3000) (Usuário: `admin` / Senha: `admin`)
  - Dashboard provisionado automaticamente: **Flauzino Assistant - Observabilidade Geral**
- **Prometheus**: [http://localhost:9090](http://localhost:9090)
  - Alvos monitorados: [http://localhost:9090/targets](http://localhost:9090/targets)

### O que é monitorado
1. **Saúde & Liveness (UP/DOWN)**: Monitoramento ativo dos 4 serviços (`finance_api`, `agent_api`, `graph_api` e `telegram_bot`).
2. **Tráfego HTTP & Erros**: Throughput (req/s), distribuição de códigos HTTP (`2xx`, `4xx`, `5xx`) e latência P95 por rota.
3. **Telegram Bot**:
   - `flauzino_telegram_messages_received_total`: Total e volume por tipo (texto, áudio, foto, comandos).
   - Detecção de tentativas de acessos não autorizados.
4. **Observabilidade de LLM**:
   - `flauzino_llm_tokens_total`: Total de tokens de prompt e completion gerados.
   - `flauzino_llm_requests_total`: Contagem de requisições enviadas ao provedor de LLM e taxas de erro.
   - `flauzino_llm_request_duration_seconds`: Latência de resposta da OpenAI.
   - `flauzino_agent_tool_executions_total`: Ferramentas acionadas pelo agente e seus tempos de execução.

---

## Rastreabilidade Distribuída (`X-Request-ID`)

O ecossistema implementa rastreabilidade distribuída de ponta a ponta com **Correlation ID** (`X-Request-ID`):

1. **Geração na Borda:** Cada comando, texto, mensagem de voz ou foto enviada pelo usuário no Telegram recebe um novo `UUIDv4` gerado no `telegram_api`.
2. **Propagação via HTTP:** O identificador é inserido no cabeçalho HTTP `X-Request-ID` de todas as chamadas feitas aos demais serviços (`agent_api` e `finance_api`).
3. **Encaminhamento Interno:** Quando a `agent_api` se comunica com a `finance_api`, o mesmo `X-Request-ID` é mantido no contexto e propagado na requisição HTTP subsequente.
4. **Logs Correlacionados:** Todos os serviços utilizam loggers que injetam automaticamente o `[request_id]` em cada linha de log. Isso permite acompanhar a jornada completa de uma requisição em todos os contêineres com um único filtro:
   ```bash
   docker-compose -f infra/docker-compose.yml logs | grep "seu-uuid-aqui"
   ```

---

## Banco de Dados (PostgreSQL)

O arquivo `infra/db/init.sql` é montado automaticamente no diretório `/docker-entrypoint-initdb.d/` na inicialização do contêiner PostgreSQL para criar:
- Extensão `uuid-ossp` para geração de identificadores universais.
- Tabelas principais: `categories`, `spents`, `limits`, `payment_methods`, `payment_owners`, `invoices`, `installments`, `subscriptions` e `chat_sessions`.
- Triggers automáticos para atualização de `updated_at`.
- Carga inicial (*seed*) de categorias essenciais (`alimentacao`, `transporte`, `lazer`, etc.).

Os dados do banco são mantidos no volume persistente `postgres_data`.

---

## Guia de Variáveis de Ambiente (`.env`)

Crie um arquivo `.env` na raiz do projeto baseado no `.env.example`.

### Banco de Dados
| Variável | Serviços | Padrão | Obrigatória? | Descrição |
|:---|:---|:---|:---:|:---|
| `POSTGRES_USER` | `db`, `finance_api`, `agent_api`, `telegram_bot` | `fake_user` | Sim | Usuário administrativo do PostgreSQL |
| `POSTGRES_PASSWORD` | `db`, `finance_api`, `agent_api`, `telegram_bot` | `fake_password` | Sim | Senha do banco PostgreSQL |
| `POSTGRES_DB` | `db`, `finance_api`, `agent_api`, `telegram_bot` | `test_db` | Sim | Nome da base de dados principal |
| `DATABASE_URL` | `finance_api`, `agent_api`, `telegram_bot` | `postgresql+asyncpg://...` | Sim | String de conexão assíncrona SQLAlchemy |
| `DB_ECHO` | `finance_api`, `agent_api` | `false` | Não | Habilita logs de queries SQL no console |

### Inteligência Artificial & Bot
| Variável | Serviços | Padrão | Obrigatória? | Descrição |
|:---|:---|:---|:---:|:---|
| `OPENAI_API_KEY` | `agent_api` | — | Sim (para Agent) | Chave de API do provedor de LLM configurado |
| `MODEL_NAME` | `agent_api` | `gpt-6-luna` | Não | Nome do modelo LLM a ser utilizado |
| `TELEGRAM_BOT_TOKEN` | `telegram_bot` | — | Sim (para Bot) | Token do bot gerado via [@BotFather](https://t.me/botfather) |
| `ALLOWED_TELEGRAM_USERNAMES` | `telegram_bot` | — | Não | Usernames do Telegram com acesso autorizado (separados por vírgula) |

### URLs de Comunicação entre Microsserviços
| Variável | Serviços que consomem | Padrão Local | Padrão Docker | Descrição |
|:---|:---|:---|:---|:---|
| `FINANCE_SERVICE_URL` | `agent_api`, `telegram_bot` | `http://localhost:8000` | `http://finance_api:8000` | URL base da Finance API |
| `AGENT_SERVICE_URL` / `AGENT_API_URL` | `telegram_bot`, `finance_api` | `http://localhost:8001` | `http://agent_api:8001` | URL base da Agent API |
| `GRAPH_SERVICE_URL` / `MCP_SERVER_URL`| `finance_api`, `agent_api`, `telegram_bot` | `http://localhost:8002` | `http://graph_api:8002` | URL base da Graph API |
| `FRONTEND_URL` | `frontend` | `http://localhost:5173` | `http://frontend:80` | URL base do Frontend |

---

## Requisitos para Desenvolvimento Fora do Docker

Caso opte por rodar os serviços Python ou Node.js diretamente no sistema operacional:

1. **Python 3.13+** e **uv**:
   ```bash
   make install
   ```
2. **Node.js 18+** e **npm** (para o Frontend):
   ```bash
   cd frontend && npm install
   ```
3. **Tesseract OCR** (necessário para extração de comprovantes na `agent_api`):
   ```bash
   # macOS (Homebrew)
   brew install tesseract tesseract-lang

   # Ubuntu / Debian
   sudo apt-get install tesseract-ocr tesseract-ocr-por
   ```
4. **Git Hooks (Pre-commit)**:
   ```bash
   make setup
   ```
