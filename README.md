# Flauzino Assistant

Este projeto tem como objetivo criar um assistente virtual capaz de lidar com registros de gastos pessoais de forma inteligente e automatizada.

## Arquitetura

O projeto é dividido em três módulos principais:

-   **`infra/`**: Contém a configuração da infraestrutura, incluindo o banco de dados PostgreSQL via Docker Compose e scripts de inicialização.
-   **`finance_api/`**: Uma API FastAPI responsável por toda a lógica de negócio e persistência de dados. Implementa uma **Camada de Serviço** para isolar regras de negócio e **Tratamento Global de Exceções**.
-   **`agent_api/`**: Uma API FastAPI que serve como a interface de conversação. Ela recebe mensagens do usuário, utiliza um LLM para extrair informações e se comunica com a `finance_api` para registrar os dados.
-   **`frontend/`**: Interface Web moderna construída com React e Vite para gerenciamento visual de gastos e limites.

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
    DATABASE_URL="postgresql+asyncpg://seu_usuario:sua_senha@localhost:5432/assistant"
    
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

3.  **Inicie o Frontend (porta 5173):**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
    -   **Acesse:** `http://localhost:5173`

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
    -d '{ "category": "comer_fora", "amount": 150.50, "payment_method": "itau", "payment_owner": "joao_lucas", "location": "restaurante_xyz" }'
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

## Próximos Passos

- [x] Fazer o agente responder bem em cenários que existem erros ao interagir com a `finance_api`
- [x] Fazer o agente confirmar os dados antes de enviar para a `finance_api`
- [ ] Criar tratamento de exeções para os repositórios
- [ ] Criar campo para informar o item que foi comprado
- [x] Criar tabela para categorias e validação dinâmica de categorias
    - [x] Criar decorator para exceções no service de categorias no finance_api
    - [x] Exceções na rota deveria estar no camada de service
- [x] Criar tabelas para cartões
    - [ ] Faltando logs
    - [ ] handlers apenas para erros 500
    - [ ] Avaliar decorators para exceções
- [x] Criar tabela para donos de cartões
    - [ ] Faltando logs
    - [ ] handlers apenas para erros 500
    - [ ] Avaliar decorators para exceções

- [ ] Implementar extração de dados de comprovantes (OCR) no agente
- [ ] Suportar comandos de voz no agente
- [ ] Criar bot no Telegram integrado à `agent_api`
- [ ] Planejar estratégia de backup do banco de dados
- [ ] Desenvolver interface web para visualizar, criar, atualizar e excluir gastos e limites
    - [x] Criar gráfico para visualizar o gasto por forma de pagamento
    - [ ] Criar uma seção para conversar com uma LLM sobre os gastos na seção de dashboard.
    - [x] Criar seção para visualização de gastos e limites com stacked charts
    - [x] Criar seção para detalhamento de gastos via tabela
    - [x] Criar seção para visualização, cadastro, edição, deleção de categorias
    - [x] Criar seção para visualização, cadastro, edição, deleção de cartões
    - [x] Criar seção para visualização, cadastro, edição, deleção de donos de cartões

