# Infraestrutura & Configurações

Guia completo da infraestrutura do **Flauzino Assistant**, abrangendo a orquestração com Docker Compose, configuração do banco de dados relacional PostgreSQL e especificação de todas as variáveis de ambiente.

---

## Topologia de Serviços

Toda a stack de microsserviços pode ser instanciada via contêineres gerenciados pelo Docker Compose (`infra/docker-compose.yml`), compartilhando uma rede interna (`default`):

| Serviço | Contêiner | Porta Exposta | Descrição |
|:---|:---|:---|:---|
| **db** | `postgres:17-alpine` | `5432:5432` | Banco de dados PostgreSQL com volume persistente e script de inicialização |
| **finance_api** | `flauzino-assistant/finance_api` | `8000:8000` | API central de regras de negócio, persistência e MCP tools |
| **agent_api** | `flauzino-assistant/agent_api` | `8001:8001` | API inteligente com integração OpenAI LLM e Tesseract OCR |
| **graph_api** | `flauzino-assistant/graph_api` | `8002:8002` | Microsserviço de renderização de gráficos com Plotly e Kaleido |
| **frontend** | `flauzino-assistant/frontend` | `5173:80` | Interface Web SPA React servida através do Nginx |
| **telegram_bot** | `flauzino-assistant/telegram_bot` | — | Worker assíncrono do bot do Telegram conectado aos serviços |

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
| Variável | Padrão | Obrigatória? | Descrição |
|:---|:---|:---:|:---|
| `POSTGRES_USER` | `fake_user` | Sim | Usuário administrativo do PostgreSQL |
| `POSTGRES_PASSWORD` | `fake_password` | Sim | Senha do banco PostgreSQL |
| `POSTGRES_DB` | `test_db` | Sim | Nome da base de dados principal |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Sim | String de conexão SQLAlchemy assíncrona com PostgreSQL |
| `DB_ECHO` | `false` | Não | Habilita logs detalhados de queries SQL geradas pelo SQLAlchemy |

### Inteligência Artificial & Bot
| Variável | Padrão | Obrigatória? | Descrição |
|:---|:---|:---:|:---|
| `OPENAI_API_KEY` | — | Sim (para Agent) | Chave de API da OpenAI para operações de chat e extração |
| `MODEL_NAME` | `gpt-6-luna` | Não | Nome do modelo LLM a ser utilizado |
| `TELEGRAM_BOT_TOKEN` | — | Sim (para Bot) | Token de autenticação do bot gerado via [@BotFather](https://t.me/botfather) |
| `ALLOWED_TELEGRAM_USERNAMES` | — | Não | Lista de usernames do Telegram (separados por vírgula) com acesso permitido ao bot |

### URLs de Comunicação entre Serviços
| Variável | Padrão Local | Padrão Docker | Descrição |
|:---|:---|:---|:---|
| `FINANCE_SERVICE_URL` | `http://localhost:8000` | `http://finance_api:8000` | Endpoint da Finance API |
| `AGENT_SERVICE_URL` / `AGENT_API_URL` | `http://localhost:8001` | `http://agent_api:8001` | Endpoint da Agent API |
| `GRAPH_SERVICE_URL` / `MCP_SERVER_URL`| `http://localhost:8002` | `http://graph_api:8002` | Endpoint da Graph API |
| `FRONTEND_URL` | `http://localhost:5173` | `http://frontend:80` | Endpoint do Frontend |

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
