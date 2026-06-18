# Flauzino Assistant

Este projeto tem como objetivo criar um assistente virtual capaz de lidar com registros de gastos pessoais de forma inteligente e automatizada.

## Arquitetura

O projeto possui a seguinte arquitetura, dividida em cinco módulos principais:

![Diagrama de Arquitetura do Sistema](docs/architecture.png)

-   **`infra/`**: Contém a configuração da infraestrutura, incluindo o banco de dados PostgreSQL via Docker Compose e scripts de inicialização.
-   **`finance_api/`**: Uma API FastAPI responsável por toda a lógica de negócio e persistência de dados. Implementa uma **Camada de Serviço** para isolar regras de negócio e **Tratamento Global de Exceções**.
-   **`agent_api/`**: Uma API FastAPI que serve como a interface de conversação. Ela recebe mensagens do usuário, utiliza um LLM para extrair informações e se comunica com a `finance_api` para registrar os dados.
-   **`telegram_api`**: Bot do Telegram para processar interações dos usuários. Agora possui um fluxo interativo (`/gasto`) que se comunica diretamente com a `finance_api`, e envia áudios/recibos para a `agent_api`.
-   **`frontend/`**: Interface Web moderna construída com React e Vite para gerenciamento visual de gastos e limites.

## Requisitos do Sistema

- **Python 3.13+** (apenas para execução local)
- **Node.js 18+** (apenas para execução local do frontend)
- **Docker** e **Docker Compose**
- **Tesseract OCR** (apenas para execução local)
  ```bash
  # Ubuntu/Debian
  sudo apt-get install tesseract-ocr
  
  # macOS
  brew install tesseract
  
  # Para suporte a português (opcional)
  sudo apt-get install tesseract-ocr-por
  ```

## Como Executar

Este projeto utiliza `uv` para gerenciamento de dependências e `Docker` para o banco de dados.

### 1. Configuração do Ambiente

1.  **Instale as dependências:**
    Você pode usar o comando Makefile (que usa o `uv sync` internamente):
    ```bash
    make install
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
    | `TELEGRAM_BOT_TOKEN` | Token do bot do Telegram (obtenha via [@BotFather](https://t.me/botfather)). | - | **Sim** (para usar o bot do Telegram) |

    Exemplo de arquivo `.env`:
    ```env
    GEMINI_API_KEY="sua_chave_api_aqui"
    DATABASE_URL="postgresql+asyncpg://seu_usuario:sua_senha@localhost:5432/assistant"
    
    # Opcionais
    MODEL_NAME="gemini-2.5-flash"
    FINANCE_SERVICE_URL="http://localhost:8000"
    AGENT_SERVICE_URL="http://localhost:8001"
    
    # Para usar o bot do Telegram
    TELEGRAM_BOT_TOKEN="seu_token_do_telegram_aqui"
    ```
    
3.  **Configure o bot do Telegram (opcional):**
    Se você deseja usar o bot do Telegram:
    1. Acesse [@BotFather](https://t.me/botfather) no Telegram
    2. Envie o comando `/newbot`
    3. Siga as instruções para escolher o nome e username do bot
    4. Copie o token fornecido e adicione ao `.env` como `TELEGRAM_BOT_TOKEN`

### 2. Infraestrutura (Para Desenvolvimento Local)

Se você deseja rodar as APIs localmente (via Python ou VS Code), inicie apenas o banco de dados:

1.  **Inicie o banco de dados PostgreSQL:**
    A partir da raiz do projeto, execute:
    ```bash
    make db-up
    ```

    > **Nota para usuários MacOS (OrbStack/Docker Desktop):**
    > Para garantir a compatibilidade, defina a variável `ARCH` antes de subir o container, ou adicione ao seu `.env`:
    > ```bash
    > export ARCH=arm64
    > make db-up
    > ```
    > Se não definido, o padrão será `amd64` (Linux/Intel).

2.  **Execute os serviços manualmente:**

    Em terminais separados, você pode usar os seguintes comandos Makefile:

    *   **Finance API:**
        ```bash
        make run-finance
        ```

    *   **Agent API:**
        ```bash
        make run-agent
        ```

    *   **Telegram Bot:**
        ```bash
        make run-telegram
        ```

    *   **Frontend:**
        ```bash
        make run-frontend
        ```

### 3. Executando Toda a Stack via Docker

Se você deseja rodar tudo (Banco, APIs, Frontend) via Docker:

1.  **Inicie tudo com um único comando:**
    ```bash
    make docker-up
    ```

    Isso irá:
    - Iniciar o banco de dados PostgreSQL.
    - Construir e iniciar a `finance_api` na porta 8000.
    - Construir e iniciar a `agent_api` na porta 8001.
    - Construir e iniciar o `frontend` na porta 5173.
    - Construir e iniciar o `telegram_bot` (se `TELEGRAM_BOT_TOKEN` estiver configurado).

    Para parar todos os containers:
    ```bash
    make docker-down
    ```

2.  **Acesse a aplicação:**
    - Frontend: `http://localhost:5173`
    - Finance docs: `http://localhost:8000/docs`
    - Agent docs: `http://localhost:8001/docs`

3.  **Verifique os logs:**
    ```bash
    docker-compose -f infra/docker-compose.yml logs -f
    ```

## Testes

O projeto utiliza `pytest` para testes unitários.

1.  **Execute os testes:**
    A partir da raiz do projeto, execute:
    ```bash
    make test
    ```

## Formatação e Linting

O projeto utiliza `black` para formatação de código (limite de 100 caracteres por linha) e `ruff` para linting.

1.  **Para formatar o código (aplica correções automaticamente):**
    ```bash
    make format
    ```

2.  **Para verificar problemas de linting e formatação (check apenas):**
    ```bash
    make lint
    ```


## Documentação das APIs

Consulte as documentações específicas de cada serviço nos seus respectivos diretórios:

- [Finance API](finance_api/README.md)
- [Frontend](frontend/README.md)

> **⚠️ Aviso Importante**
> As aplicações **Agent API** e **Telegram Bot** estão atualmente **em revisão** e podem sofrer alterações significativas na sua estrutura e funcionamento.
- [Agent API (Em Revisão)](agent_api/README.md)
- [Telegram Bot (Em Revisão)](telegram_api/README.md)
