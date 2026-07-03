# Especificação: Consulta de Saldo e Limites por Categoria

Esta especificação define o plano de implementação técnica para habilitar consultas síncronas (comandos e texto livre) e notificações assíncronas (cron) referentes aos limites e saldos disponíveis do usuário.

## 1. Visão Geral
A funcionalidade permitirá que o usuário saiba quanto já gastou e quanto ainda pode gastar em cada categoria no mês vigente.
- **Síncrono (Comando):** Usuário digita `/limites` ou `/saldo` no Telegram e recebe um relatório.
- **Síncrono (Linguagem Natural):** Usuário digita "quanto ainda tenho para gastar com mercado?" e o agente responde.
- **Assíncrono (Proativo):** Toda sexta-feira, o bot envia um resumo automático do saldo das categorias.

---

## 2. Implementação no Backend (`finance_api`)

Precisamos expor um endpoint que consolide os gastos do mês atual contra os limites definidos, retornando o saldo disponível.

### 2.1. Schemas (`schemas/limits.py`)
Criar o modelo de resposta para o saldo da categoria:
```python
class CategoryBalance(BaseModel):
    category: str
    limit: float
    spent: float
    available: float
    percentage_used: float
```

### 2.2. Repository e Service (`services/limits.py` e `services/spents.py`)
- Adicionar no `SpendingLimitService` (ou em um novo `BalanceService`) uma função `get_monthly_balance(reference_month: str) -> List[CategoryBalance]`.
- A lógica buscará todos os limites cadastrados (via `SpendingLimitRepository`).
- Buscará a soma de gastos (`amount`) no mês de referência agrupados por categoria (via `SpentRepository`).
- Fará o cálculo: `available = limit - spent`.

### 2.3. Router (`routers/limits.py`)
- Novo endpoint: `GET /limits/balance` (recebendo opcionalmente `reference_month`).
- Retorna uma lista de `CategoryBalance`.

---

## 3. Implementação no Agent (`agent_api`)

O agente (LLM) precisa conseguir identificar a intenção de consulta de saldo e retornar essa informação.

### 3.1. Schemas (`schemas/assistant.py`)
- Adicionar o campo booleano `is_balance_query` ao `AssistantResponse`.

### 3.2. LLM e Prompts (`services/llm.py`)
- Atualizar o `system_prompt` para instruir o LLM: se o usuário perguntar sobre saldos, limites ou o quanto pode gastar, marcar `is_balance_query = True`.

### 3.3. Orquestração (`routers/chat.py` ou `services/chat.py`)
- Se `is_balance_query == True`, a `agent_api` deve:
  1. Fazer uma requisição HTTP para o `finance_api` (`GET /limits/balance`).
  2. Injetar o resultado em uma segunda chamada ao LLM (passando os dados do backend para que o LLM formate uma resposta em linguagem natural com o saldo atual) ou formatar a resposta textualmente de maneira padronizada.
  3. Retornar a string amigável para o `telegram_api`.

---

## 4. Implementação no Bot do Telegram (`telegram_api`)

### 4.1. Habilitar Texto Livre (`main.py` e `message_handler.py`)
- Em `main.py`, trocar o registro do tratador de texto `handle_unknown_text_message` para voltar a usar o `handle_text_message` (que chama a `agent_api`), reativando a conversa natural.

### 4.2. Comando Síncrono (`command_handler.py`)
- Criar a função `limites_command`.
- Fazer uma chamada direta ao `finance_api` (`GET /limits/balance`).
- Formatar uma mensagem Markdown com os valores retornados (usando emojis, ex: 🟢 para disponível alto, 🔴 para estourado) e enviá-la ao usuário.
- Registrar o comando em `main.py` (`CommandHandler("limites", limites_command)` e `CommandHandler("saldo", limites_command)`).

### 4.3. Job Assíncrono (Cron) (`scheduler.py` ou em `main.py`)
- Utilizar a `JobQueue` embutida do pacote `python-telegram-bot` (que já roda de forma assíncrona com o loop da aplicação).
- Agendar um job para rodar toda sexta-feira em um horário configurável (ex: 10h da manhã).
- O job fará a requisição ao `finance_api` para obter o saldo e enviará proativamente a mensagem formatada de relatório de saúde financeira para o chat_id do dono (ou para os usuários permitidos).
