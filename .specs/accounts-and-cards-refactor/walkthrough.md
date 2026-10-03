# Walkthrough: Refatoração de Contas Bancárias e Cartões de Crédito

Implementamos a transição arquitetural de métodos de pagamento planos para uma hierarquia estruturada:
$$\text{Conta Bancária (Account)} \longrightarrow \text{Cartões de Crédito (CreditCard)}$$

---

## 1. O que foi implementado

### 1.1. Banco de Dados & Migração
- Criadas as tabelas `accounts` e `credit_cards` no PostgreSQL com integridade referencial (`ON DELETE CASCADE` de cartões vinculados a contas).
- Adicionadas as colunas `account_id`, `credit_card_id` e `payment_type` nas tabelas `spents`, `incomes`, `subscriptions` e `invoices`.
- Migração e backfill executados com sucesso para todas as despesas e faturas históricas existentes.
- Seeds inseridos no `infra/db/init.sql`:
  - **Contas**: `itau_joao`, `nubank_joao`, `nubank_lailla`, `picpay_joao`, `c6_joao`, `dinheiro_vivo`.
  - **Cartões**: `itau_card_joao`, `nubank_card_joao`, `nubank_card_lailla`, `picpay_card_joao`, `c6_card_joao`.

### 1.2. Backend Core (`finance_api`)
- **Models**:
  - `finance_api/models/accounts.py`: `Account` com relacionamento `credit_cards` (`lazy="selectin"`).
  - `finance_api/models/credit_cards.py`: `CreditCard` com chave estrangeira `account_id`.
  - `finance_api/models/incomes.py`, `spents.py`, `subscriptions.py`, `invoices.py` atualizados.
- **Schemas Pydantic**:
  - `finance_api/schemas/accounts.py`: `AccountBase`, `AccountCreate`, `AccountUpdate`, `AccountResponse`.
  - `finance_api/schemas/credit_cards.py`: `CreditCardBase`, `CreditCardCreate`, `CreditCardUpdate`, `CreditCardResponse`.
- **Repositories & Services**:
  - `AccountRepository` e `AccountService` com `@handle_service_errors`.
  - `CreditCardRepository` e `CreditCardService` validando se a conta emissora vinculada existe.
- **Routers**:
  - `GET`, `POST`, `PUT`, `DELETE` em `/accounts/`.
  - `GET`, `POST`, `PUT`, `DELETE` em `/credit-cards/`.
- **Ferramentas MCP**:
  - `list_accounts(owner=...)`
  - `list_credit_cards()`

### 1.3. IA & Processamento de Linguagem Natural (`agent_api`)
- `FinanceService`: adicionados métodos `get_accounts()` e `get_credit_cards()` com cache TTL in-memory.
- System prompt atualizado dinamicamente com as contas e cartões disponíveis, orientando a IA:
  - Compras a crédito $\rightarrow$ vincular ao cartão de crédito.
  - Débito, Pix ou Dinheiro $\rightarrow$ vincular à conta bancária.
  - Receitas / entradas financeiras $\rightarrow$ vincular à conta bancária de crédito.

### 1.4. Bot do Telegram (`telegram_api`)
- Adicionados métodos de busca de contas e cartões no `http_client.py`.
- No fluxo `/receita`, agora é exibido o seletor com as contas bancárias cadastradas (`get_valid_accounts`).

### 1.5. Interface Web (`frontend`)
- Criada a página `frontend/src/pages/AccountsPage.tsx`:
  - Listagem de todas as contas cadastradas com seus respectivos dados (banco, titular, tipo).
  - Accordion interativo exibindo todos os cartões de crédito vinculados a cada conta, com dia de fechamento, dia de vencimento e limite.
  - Modais para criação e edição de Contas e Cartões.
  - Modais de confirmação de exclusão com alerta de cascata.
- Atualizado o menu lateral e roteamento no `frontend/src/App.tsx` com a aba **"Contas & Cartões"**.
- TypeScript build (`npm run build`) validado com sucesso.

---

## 2. Testes e Qualidade

- **Testes Unitários**: 295 testes executados e passando (`uv run pytest`).
- **Formatador**: `make format` executado com sucesso (Black).
- **Linter**: `make lint` executado com sucesso (Ruff - 0 erros).
- **Containers Docker**: Containers reconstruídos e ativos (`infra-finance_api-1`, `infra-agent_api-1`, `infra-telegram_bot-1`, `infra-frontend-1`).
