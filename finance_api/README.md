# Finance API

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

