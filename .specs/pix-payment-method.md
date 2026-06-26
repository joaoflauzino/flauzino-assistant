# Adição do PIX como Forma de Pagamento

## 1. Análise
A alteração afeta a inicialização do banco de dados (infra) e o fallback de opções de formas de pagamento no LLM (agent_api). Não há impacto direto nos modelos ou rotas da API, pois as formas de pagamento são dinâmicas, limitadas apenas pelo seed inicial ou inserção no banco.

## 2. Especificação
- **Models / Repositories / Services / Routers**: Não há necessidade de alterações, o modelo e as rotas já suportam adição de dados genéricos de métodos de pagamento.
- **Banco de Dados (infra/db/init.sql)**:
  - Adicionar o registro `('pix', 'Pix')` no bloco de `INSERT INTO payment_methods`.
- **LLM Service (agent_api/services/llm.py)**:
  - Adicionar `pix` na string de retorno de fallback da função `get_valid_payment_methods`.

## 3. Plano de Testes
- A alteração é apenas de inserção de registro e atualização de string de fallback, não quebra testes existentes. 
- Será verificado se a adição no `init.sql` funciona via execução de lint/formatação e validação visual.
