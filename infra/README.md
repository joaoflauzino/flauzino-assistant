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

---

## Observabilidade (Prometheus & Grafana)

A stack inclui monitoramento de métricas em tempo real e visualização de dashboards através de contêineres dedicados:

- **Prometheus:** Acessível em [http://localhost:9090](http://localhost:9090). Coleta métricas das rotas `/metrics` dos serviços Python a cada 10 segundos.
- **Grafana:** Acessível em [http://localhost:3000](http://localhost:3000). Pré-configurado com login `admin`/`admin` e provisionamento automático de datasource e dashboards:
  - **Overview Geral:** Métricas de tráfego HTTP, latência e status dos microsserviços.
  - **Agent & LLM Metrics:** Contadores de tokens gerados, uso de MCP tools e execuções de OCR.
  - **Telegram Bot Activity:** Contadores de mensagens recebidas e enviadas agrupadas por tipo.

---

## Guia de Variáveis de Ambiente (.env)

Todas as configurações sensíveis e URLs de integração entre microsserviços são parametrizadas no `.env`. Utilize o [.env.example](../.env.example) como modelo base.

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

### Backup & Notificações
| Variável | Serviços | Padrão | Obrigatória? | Descrição |
|:---|:---|:---|:---:|:---|
| `RCLONE_REMOTE` | Script de Backup | `gdrive:flauzino-backups` | Não | Destino do remote configurado no Rclone |
| `TELEGRAM_CHAT_ID` | Script de Backup | — | Não | ID numérico do usuário/canal para alertas |

---

## Backup Automatizado e Retenção

Para detalhes sobre o script de backup unificado (`scripts/backup_rclone.sh`), políticas de retenção (PostgreSQL por 180 dias e logs por 30 dias) e agendamento no Linux/Raspberry Pi com Systemd Timer, consulte o [`infra/server/README.md`](server/README.md).

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
