# Flauzino Assistant

Este projeto tem como objetivo criar um assistente virtual capaz de lidar com registros de gastos pessoais de forma inteligente e automatizada.

## Arquitetura

O projeto é dividido em três módulos principais:

-   **`infra/`**: Contém a configuração da infraestrutura, incluindo o banco de dados PostgreSQL via Docker Compose e scripts de inicialização.
-   **`finance_api/`**: Uma API FastAPI responsável por toda a lógica de negócio e persistência de dados. Ela gerencia os gastos e limites no banco de dados.
-   **`agent_api/`**: Uma API FastAPI que serve como a interface de conversação. Ela recebe mensagens do usuário, utiliza um LLM para extrair informações e se comunica com a `finance_api` para registrar os dados.

## Como Executar

Este projeto utiliza `uv` para gerenciamento de dependências e `Docker` para o banco de dados.

### 1. Configuração do Ambiente

1.  **Instale as dependências:**
    ```bash
    uv sync
    ```

2.  **Crie as variáveis de ambiente:**
    Crie um arquivo `.env` na raiz do projeto ou exporte as variáveis necessárias.
    
    | Variável | Descrição | Padrão | Obrigatório? |
    | :--- | :--- | :--- | :--- |
    | `GEMINI_API_KEY` | Chave de API do Google Gemini. | - | **Sim** |
    | `DATABASE_URL` | URL de conexão com o banco de dados. | - | **Sim** (Local via Docker) |
    | `MODEL_NAME` | Modelo do Gemini a ser utilizado. | `gemini-2.5-flash` | Não |
    | `FINANCE_SERVICE_URL` | URL da API Financeira (usada pelo Agente). | `http://localhost:8000` | Não |
    | `AGENT_SERVICE_URL` | URL da API do Agente (usada pela Finance API). | `http://localhost:8001` | Não |

    Exemplo de arquivo `.env`:
    ```env
    GEMINI_API_KEY="sua_chave_api_aqui"
    DATABASE_URL="postgresql+asyncpg://flauzino:password@localhost:5432/assistant"
    
    # Opcionais
    MODEL_NAME="gemini-2.5-flash"
    FINANCE_SERVICE_URL="http://localhost:8000"
    AGENT_SERVICE_URL="http://localhost:8001"
    ```

### 2. Infraestrutura

1.  **Inicie o banco de dados PostgreSQL:**
    A partir da raiz do projeto, execute:
    ```bash
    docker-compose -f infra/docker-compose.yml up -d
    ```

### 3. Executando os Serviços

Você precisará de dois terminais para rodar as duas APIs simultaneamente.

1.  **Inicie a API Financeira (porta 8000):**
    ```bash
    uv run uvicorn finance_api.main:app --port 8000 --reload
    ```
    -   **Docs (Swagger):** `http://localhost:8000/docs`

2.  **Inicie a API do Agente (porta 8001):**
    ```bash
    uv run uvicorn agent_api.main:app --port 8001 --reload
    ```
    -   **Docs (Swagger):** `http://localhost:8001/docs`

## Testes

O projeto utiliza `pytest` para testes unitários.

1.  **Instale as dependências de desenvolvimento:**
    ```bash
    uv sync --group dev
    ```

2.  **Execute os testes:**
    A partir da raiz do projeto, execute:
    ```bash
    pytest
    ```

## Documentação das APIs

### Finance API

Interação direta com o banco de dados.

#### Registrar um Gasto (POST /spents)

```bash
curl -X 'POST' \
  'http://localhost:8000/spents' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "category": "comer_fora",
  "amount": 150.50,
  "payment_method": "itau",
  "payment_owner": "joao_lucas",
  "location": "Restaurante X"
}'
```

#### Listar Gastos (GET /spents)

```bash
curl -X 'GET' 'http://localhost:8000/spents' -H 'accept: application/json'
```

#### Criar/Atualizar Limite (POST /limits)

```bash
curl -X 'POST' \
  'http://localhost:8000/limits' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "category": "comer_fora",
  "amount": 2000.00
}'
```

#### Listar Limites (GET /limits)

```bash
curl -X 'GET' 'http://localhost:8000/limits' -H 'accept: application/json'
```

### Agent API

Interface de conversação para interagir com o sistema.

#### Enviar Mensagem (POST /chat)

```bash
curl -X 'POST' \
  'http://localhost:8001/chat' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "message": "gastei 50 reais no mercado com o cartão do itau do joao lucas",
  "session_id": "optional-uuid"
}'
```
