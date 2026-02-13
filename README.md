# Flauzino Assistant

Este projeto tem como objetivo criar um assistente virtual capaz de lidar com registros de gastos pessoais de forma inteligente e automatizada.

## Arquitetura

O projeto é dividido em quatro módulos principais:

-   **`infra/`**: Contém a configuração da infraestrutura, incluindo o banco de dados PostgreSQL via Docker Compose e scripts de inicialização.
-   **`finance_api/`**: Uma API FastAPI responsável por toda a lógica de negócio e persistência de dados. Implementa uma **Camada de Serviço** para isolar regras de negócio e **Tratamento Global de Exceções**.
-   **`agent_api/`**: Uma API FastAPI que serve como a interface de conversação. Ela recebe mensagens do usuário, utiliza um LLM para extrair informações e se comunica com a `finance_api` para registrar os dados.
-   **`telegram_api/`**: Bot do Telegram que se comunica com a `agent_api` via HTTP para processar mensagens e recibos enviados pelos usuários.
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
    docker-compose --env-file .env -f infra/docker-compose.yml up -d db
    ```

    > **Nota para usuários MacOS (OrbStack/Docker Desktop):**
    > Para garantir a compatibilidade, defina a variável `ARCH` antes de subir o container, ou adicione ao seu `.env`:
    > ```bash
    > export ARCH=arm64
    > docker-compose -f infra/docker-compose.yml up -d db
    > ```
    > Se não definido, o padrão será `amd64` (Linux/Intel).

2.  **Execute os serviços manualmente:**

    Em terminais separados, execute cada serviço:

    *   **Finance API:**
        ```bash
        uv run uvicorn finance_api.main:app --port 8000 --reload
        ```

    *   **Agent API:**
        ```bash
        uv run uvicorn agent_api.main:app --port 8001 --reload
        ```

    *   **Telegram Bot:**
        ```bash
        uv run python -m telegram_api.main
        ```

    *   **Frontend:**
        ```bash
        cd frontend
        npm install
        npm run dev
        ```

### 3. Executando Toda a Stack via Docker

Se você deseja rodar tudo (Banco, APIs, Frontend) via Docker:

1.  **Inicie tudo com um único comando:**
    ```bash
    docker-compose --env-file .env -f infra/docker-compose.yml up -d --build
    ```

    Isso irá:
    - Iniciar o banco de dados PostgreSQL.
    - Construir e iniciar a `finance_api` na porta 8000.
    - Construir e iniciar a `agent_api` na porta 8001.
    - Construir e iniciar o `frontend` na porta 5173.
    - Construir e iniciar o `telegram_bot` (se `TELEGRAM_BOT_TOKEN` estiver configurado).

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
    uv run pytest
    ```

## Documentação das APIs

### Finance API

Interação direta com o banco de dados. A API suporta operações CRUD completas para gastos.

#### Paginação e Estrutura de Resposta

Os endpoints de listagem (`GET`) utilizam paginação baseada em página.

-   **Parâmetros de Consulta:**
    -   `page`: Número da página (padrão: `1`).
    -   `size`: Quantidade de itens por página (padrão: `10`).

-   **Estrutura da Resposta:**
    ```json
    {
      "items": [ ... ],
      "total": 50,
      "page": 1,
      "size": 10,
      "pages": 5
    }
    ```


#### Categories (Categorias)

Gerencie categorias de forma dinâmica via API.

- **Listar Categorias (GET /categories)**
  ```bash
  curl -X 'GET' 'http://localhost:8000/categories?page=1&size=100'
  ```

- **Obter por ID (GET /categories/{id})**
  ```bash
  curl -X 'GET' 'http://localhost:8000/categories/{category-id}'
  ```

- **Criar Categoria (POST /categories)**
  ```bash
  curl -X 'POST' 'http://localhost:8000/categories' \
    -H 'Content-Type: application/json' \
    -d '{ "key": "pets", "display_name": "Animais de Estimação" }'
  ```

- **Atualizar (PUT /categories/{id})**
  ```bash
  curl -X 'PUT' 'http://localhost:8000/categories/{category-id}' \
    -H 'Content-Type: application/json' \
    -d '{ "display_name": "Pets e Veterinário" }'
  ```

- **Deletar (DELETE /categories/{id})**
  ```bash
  curl -X 'DELETE' 'http://localhost:8000/categories/{category-id}'
  ```

> **Nota:** Após criar uma categoria, você pode usá-la imediatamente em gastos e limites usando a `key` definida.

#### Spents (Gastos)

- **Criar (POST /spents)**
  ```bash
  curl -X 'POST' 'http://localhost:8000/spents' \
    -H 'Content-Type: application/json' \
    -d '{ "category": "comer_fora", "amount": 150.50, "item_bought": "jantar", "payment_method": "itau", "payment_owner": "joao_lucas", "location": "restaurante_xyz" }'
  ```

- **Listar (GET /spents)**
  ```bash
  curl -X 'GET' 'http://localhost:8000/spents?page=1&size=10'
  ```

- **Obter por ID (GET /spents/{id})**
  ```bash
  curl -X 'GET' 'http://localhost:8000/spents/56c694c0-1c3b-4163-8d6f-76140d5e3e87'
  ```

- **Atualizar (PATCH /spents/{id})**
  ```bash
  curl -X 'PATCH' 'http://localhost:8000/spents/56c694c0-1c3b-4163-8d6f-76140d5e3e87' \
    -H 'Content-Type: application/json' \
    -d '{ "amount": 200.00 }'
  ```

- **Deletar (DELETE /spents/{id})**
  ```bash
  curl -X 'DELETE' 'http://localhost:8000/spents/56c694c0-1c3b-4163-8d6f-76140d5e3e87'
  ```

#### Limits (Limites de Gastos)

- **Criar Limite (POST /limits)**
  ```bash
  curl -X 'POST' 'http://localhost:8000/limits' \
    -H 'Content-Type: application/json' \
    -d '{ "category": "comer_fora", "amount": 2000.00 }'
  ```

- **Listar Limites (GET /limits)**
  ```bash
  curl -X 'GET' 'http://localhost:8000/limits?page=1&size=10'
  ```

- **Obter por ID (GET /limits/{id})**
  ```bash
  curl -X 'GET' 'http://localhost:8000/limits/85889a09-85dc-4969-9dea-4abc6ac4dbb8'
  ```

- **Atualizar (PATCH /limits/{id})**
  ```bash
  curl -X 'PATCH' 'http://localhost:8000/limits/85889a09-85dc-4969-9dea-4abc6ac4dbb8' \
    -H 'Content-Type: application/json' \
    -d '{ "amount": 3000.00 }'
  ```

- **Deletar (DELETE /limits/{id})**
  ```bash
  curl -X 'DELETE' 'http://localhost:8000/limits/85889a09-85dc-4969-9dea-4abc6ac4dbb8'
  ```

#### Payment Methods (Formas de Pagamento)

- **Listar (GET /payment-methods)**
  ```bash
  curl -X 'GET' 'http://localhost:8000/payment-methods?page=1&size=100'
  ```

- **Criar (POST /payment-methods)**
  ```bash
  curl -X 'POST' 'http://localhost:8000/payment-methods' \
    -H 'Content-Type: application/json' \
    -d '{ "key": "visa", "display_name": "Visa" }'
  ```

- **Atualizar (PUT /payment-methods/{id})**
  ```bash
  curl -X 'PUT' 'http://localhost:8000/payment-methods/{id}' \
    -H 'Content-Type: application/json' \
    -d '{ "display_name": "Visa Platinum" }'
  ```

- **Deletar (DELETE /payment-methods/{id})**
  ```bash
  curl -X 'DELETE' 'http://localhost:8000/payment-methods/{id}'
  ```

#### Payment Owners (Donos de Pagamento)

- **Listar (GET /payment-owners)**
  ```bash
  curl -X 'GET' 'http://localhost:8000/payment-owners?page=1&size=100'
  ```

- **Criar (POST /payment-owners)**
  ```bash
  curl -X 'POST' 'http://localhost:8000/payment-owners' \
    -H 'Content-Type: application/json' \
    -d '{ "key": "fernanda", "display_name": "Fernanda" }'
  ```

- **Atualizar (PUT /payment-owners/{id})**
  ```bash
  curl -X 'PUT' 'http://localhost:8000/payment-owners/{id}' \
    -H 'Content-Type: application/json' \
    -d '{ "display_name": "Maria Fernanda" }'
  ```

- **Deletar (DELETE /payment-owners/{id})**
  ```bash
  curl -X 'DELETE' 'http://localhost:8000/payment-owners/{id}'
  ```

### Agent API

Interface de conversação para interagir com o sistema.

#### Enviar Mensagem (POST /chat)

```bash
curl -X 'POST' \
  'http://localhost:8001/chat' \
  -H 'Content-Type: application/json' \
  -d '{
  "message": "gastei 50 reais no mercado com o cartão do itau do joao lucas",
  "session_id": "optional-uuid"
}'
```

#### Extrair Texto de Recibo (POST /ocr/extract)

Extrai texto de uma imagem de recibo usando OCR.

```bash
curl -X 'POST' \
  'http://localhost:8001/ocr/extract' \
  -F 'file=@/path/to/receipt.jpg'
```

**Resposta:**
```json
{
  "text": "SUPERMERCADO XYZ\nValor: R$ 132,07\n...",
  "confidence": 85.5,
  "char_count": 1235,
  "filename": "receipt.jpg"
}
```

#### Processar Recibo Completo (POST /ocr/process-receipt)

Processa uma imagem de recibo e inicia/continua uma sessão de chat.

```bash
curl -X 'POST' \
  'http://localhost:8001/ocr/process-receipt' \
  -F 'file=@/path/to/receipt.jpg'
```

**Resposta:**
```json
{
  "response": "Para registrar o gasto, preciso do método de pagamento utilizado (Itau, PicPay, XP, Nubank ou C6), quem foi o proprietário...",
  "session_id": "9a144f4c-016e-4792-936f-504fe524bf10",
  "history": [
    {
      "role": "user",
      "content": "Aqui está o texto extraído de um recibo...\n\nPor favor, extraia as informações de gastos."
    },
    {
      "role": "assistant",
      "content": "Para registrar o gasto, preciso do método de pagamento..."
    }
  ]
}
```

**Você pode então continuar a conversa usando o `/chat` com o `session_id` retornado:**

```bash
curl -X 'POST' \
  'http://localhost:8001/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "foi com o cartão do itau do joao lucas",
    "session_id": "9a144f4c-016e-4792-936f-504fe524bf10"
  }'
```

**Formatos suportados:** JPG, JPEG, PNG, WebP, BMP, TIFF  
**Tamanho máximo:** 10MB

## Usando o Bot do Telegram

O Flauzino Assistant inclui um bot do Telegram que permite registrar gastos e processar recibos diretamente pelo aplicativo de mensagens.

### Como Usar
    
Certifique-se de que o serviços estão rodando conforme descrito na seção "Executando os Serviços".

1. **Encontre seu bot:**
   - Procure pelo username que você definiu no BotFather.
   - Envie `/start` para iniciar.

### Comandos Disponíveis

- `/start` - Mensagem de boas-vindas e instruções
- `/help` - Mostra como usar o bot com exemplos

### Como Usar

**Registrar gastos via mensagem de texto:**
```
gastei 50 reais no mercado com o cartão do itau do joao lucas
```

O bot irá:
1. Processar sua mensagem
2. Pedir informações faltantes (se houver)
3. Confirmar os dados antes de registrar
4. Salvar no banco de dados via `agent_api` → `finance_api`

**Enviar recibos via foto:**
1. Tire uma foto do recibo
2. Envie a foto para o bot
3. O bot irá extrair o texto automaticamente (OCR)
4. Pedir informações adicionais se necessário
5. Confirmar e registrar o gasto

### Sessões de Conversa

- Cada chat do Telegram tem sua própria sessão
- O bot lembra do contexto da conversa
- Você pode corrigir ou adicionar informações a qualquer momento
- Todas as sessões são armazenadas no banco de dados

## Próximos Passos

- [x] Fazer o agente responder bem em cenários que existem erros ao interagir com a `finance_api`
- [x] Fazer o agente confirmar os dados antes de enviar para a `finance_api`
- [x] Criar campo para informar o item que foi comprado
- [x] Criar tabela para categorias e validação dinâmica de categorias
    - [x] Criar decorator para exceções no service de categorias no finance_api
    - [x] Exceções na rota deveria estar no camada de service
- [x] Criar tabelas para cartões
- [x] Criar tabela para donos de cartões
- [x] Implementar extração de dados de comprovantes (OCR) no agente
  - [x] Avaliar qualidade do OCR
- [x] Criar bot no Telegram integrado à `agent_api`
- [ ] Garantir execução via docker e via python
- [ ] Suportar comandos de voz no agente
- [ ] Planejar estratégia de backup do banco de dados
- [x] Desenvolver interface web para visualizar, criar, atualizar e excluir gastos e limites
    - [x] Criar gráfico para visualizar o gasto por forma de pagamento
    - [x] Criar gráfico para visualizar gastos dos top 10 itens comprados
    - [ ] Criar uma seção para conversar com uma LLM sobre os gastos na seção de dashboard.
    - [x] Criar seção para visualização de gastos e limites com stacked charts
    - [x] Criar seção para detalhamento de gastos via tabela
    - [x] Criar seção para visualização, cadastro, edição, deleção de categorias
    - [x] Criar seção para visualização, cadastro, edição, deleção de cartões
    - [x] Criar seção para visualização, cadastro, edição, deleção de donos de cartões