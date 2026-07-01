# Regras de Validação e Melhoria de Erros

Este documento detalha a refatoração arquitetural para matar a entidade "Titular" fundindo-a aos métodos de pagamento (já que as faturas são estritamente separadas por pessoa física e cartão) e a melhoria no tratamento de erros do sistema.

## Objetivo
1. **Padrão de Cartões de Crédito:** Ajustar o arquivo de infraestrutura para que todos os cartões (exceto Pix) possuam datas de fechamento (`02`) e vencimento (`10`) padrões e a flag `is_credit_card`.
2. **Matar a Entidade "Titular":** Como as faturas são separadas (João tem o Nubank dele, Lailla tem o dela), a entidade `PaymentOwner` perde o sentido. Teremos apenas `PaymentMethods` que já carregam no nome e na chave quem é o dono real da fatura (ex: `nubank_lailla`, `itau_joao`).
3. **Clareza de Erros no Frontend:** Expor os motivos de recusa (ValidationErrors, EntityConflictErrors, etc.) diretamente em Alertas na UI usando um Interceptador Global do Axios.

## Proposed Changes

### `infra/db`
#### [MODIFY] `infra/db/init.sql`
- **Remover** a tabela `payment_owners`.
- **Remover** a coluna `payment_owner` nas tabelas `spents` e `subscriptions`.
- **Atualizar** os inserts de `payment_methods`:
  - `('itau_joao', 'Itaú (João Lucas)', true, 2, 10)`
  - `('nubank_joao', 'Nubank (João Lucas)', true, 2, 10)`
  - `('nubank_lailla', 'Nubank (Lailla)', true, 2, 10)`
  - `('picpay_joao', 'PicPay (João Lucas)', true, 2, 10)`
  - `('c6_joao', 'C6 (João Lucas)', true, 2, 10)`
  - `('pix_joao', 'Pix (João Lucas)', false, null, null)`

### `finance_api`
- Remover as colunas `payment_owner` de `models` e `schemas` (Spents e Subscriptions).
- Remover toda a validação complexa de dentro dos Services (pois o próprio método de pagamento selecionado já é a regra viva).

### `frontend`
- No `SpentsPage.tsx` (e outras páginas caso existam), remover a requisição para `/payment-owners/`, o combobox de Titular, e as colunas nas tabelas.
- O campo `payment_method` passa a ser o único exibido (ex: "Nubank (Lailla)").
- Manter o `api.interceptors.response.use` adicionado em `api.ts` para que qualquer erro futuro da API (422, 404, 409) mostre o `error.response.data.detail` no frontend.
