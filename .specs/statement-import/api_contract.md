# Contrato de API — Importação de Extratos

Contrato fixo entre `finance_api` (backend), `agent_api` (classificação por LLM) e `frontend`.
Base do front: `axios` com `baseURL: '/api'` (nginx → `finance_api`).

## 1. Enums (strings)

| Campo | Valores |
| :-- | :-- |
| `kind` | `EXPENSE`, `INCOME`, `TRANSFER`, `INVOICE_PAYMENT`, `REFUND` |
| `direction` | `IN`, `OUT` |
| `status` (transação) | `PENDING`, `APPROVED`, `COMMITTED`, `IGNORED`, `LINKED` |
| `suggestion_source` | `RULE`, `MEMORY`, `LLM`, `null` |
| `payment_type` | `PIX`, `DEBIT`, `CASH`, `TRANSFER`, `OTHER` |

Semântica: `PENDING` = aguardando revisão · `APPROVED` = aprovada, aguardando "Importar aprovadas" ·
`COMMITTED` = efetivada (gerou gasto/receita, ou só processada se `kind` ∈ TRANSFER/INVOICE_PAYMENT/REFUND) ·
`IGNORED` = descartada pelo usuário · `LINKED` = vinculada a um gasto/receita já existente.

## 2. `finance_api`

### Objetos

`StagedTransaction`
```json
{
  "id": "uuid", "batch_id": "uuid",
  "account_id": "uuid|null", "credit_card_id": "uuid|null",
  "occurred_at": "2026-09-09T12:00:00-03:00", "posted_at": "…|null",
  "raw_title": "Pix enviado para ZILMA MARIA DE FREITAS",
  "raw_description": "TRANSF ENVIADA PIX",
  "merchant": "ZILMA MARIA DE FREITAS",
  "amount": 180.0, "direction": "OUT",
  "kind": "EXPENSE", "payment_type": "PIX",
  "suggested_category": "moradia|null",
  "suggestion_source": "MEMORY|null", "confidence": 0.9,
  "category": "moradia|null",
  "description": "texto editável (<=50 chars)",
  "location": "texto editável",
  "status": "PENDING",
  "possible_duplicate": { "type": "spent|income", "id": "uuid", "label": "Mercado", "amount": 180.0, "date": "2026-09-08" } ,
  "committed_spent_id": "uuid|null", "committed_income_id": "uuid|null"
}
```
(`possible_duplicate` é `null` quando não há.) `category` vem pré-preenchida com a sugestão quando existe.

`ImportBatch`
```json
{
  "id": "uuid", "filename": "extrato.csv", "parser": "c6_checking_csv",
  "account_id": "uuid|null", "account_name": "C6 (João Lucas)|null",
  "period_start": "2026-08-04|null", "period_end": "2026-10-03|null",
  "total_rows": 41, "new_rows": 38, "duplicate_rows": 3,
  "possible_duplicates": 2, "ai_used": true,
  "created_at": "…",
  "counts": { "pending": 30, "approved": 0, "committed": 0, "ignored": 0, "linked": 0 }
}
```
`duplicate_rows` = linhas do arquivo que já existiam (descartadas pelo fingerprint).

### Rotas (prefixo `/imports`)

| Método | Rota | Corpo / Query | Resposta |
| :-- | :-- | :-- | :-- |
| `POST` | `/imports` | `multipart/form-data`: `file` (CSV), `account_id` (uuid) | `ImportBatch` (201). 409 se o mesmo arquivo já foi importado; 422 se formato não reconhecido |
| `GET` | `/imports` | — | `ImportBatch[]` (mais recentes primeiro) |
| `GET` | `/imports/summary` | — | `{ "pending": 12, "approved": 3 }` |
| `GET` | `/imports/transactions` | `status`, `batch_id`, `kind`, `only_duplicates` (bool), `only_unclassified` (bool), `page`, `size` | `{items: StagedTransaction[], total, page, size, pages}` |
| `PATCH` | `/imports/transactions/{id}` | `{category?, kind?, description?, location?, status?: "PENDING"\|"APPROVED"\|"IGNORED", remember?: bool}` | `StagedTransaction` |
| `POST` | `/imports/transactions/bulk` | `{ids: uuid[], action: "approve"\|"ignore"\|"reopen"\|"set_category", category?, remember?: bool}` | `{updated: n, skipped: n, errors: [{id, error}]}` |
| `POST` | `/imports/transactions/{id}/link` | — | `StagedTransaction` (status `LINKED`) |
| `POST` | `/imports/commit` | `{batch_id?: uuid}` | `{committed_spents: n, committed_incomes: n, processed_without_record: n, failed: [{id, error}]}` |
| `POST` | `/imports/{batch_id}/classify` | — | `{classified: n, ai_used: bool}` (reclassifica PENDING sem sugestão) |
| `GET` | `/import-rules` | — | `ImportRule[]` |
| `DELETE` | `/import-rules/{id}` | — | 204 |

`ImportRule`: `{id, pattern, match_type, direction, kind, category, hits, source: "SEED"|"LEARNED"}`.

Regras de negócio relevantes à UI:
- Para aprovar (`status: "APPROVED"`) uma transação `EXPENSE`/`INCOME`, `category` precisa estar definida (senão 422).
  `kind` ∈ `TRANSFER`/`INVOICE_PAYMENT`/`REFUND` aprova sem categoria.
- `remember: true` no PATCH/bulk de aprovação grava a regra aprendida do comerciante (padrão no front: `true`).
- Bulk `approve` **pula** (`skipped`) linhas com `possible_duplicate` e linhas EXPENSE/INCOME sem categoria.
- Se `kind` mudar para `EXPENSE`/`INCOME`, a categoria anterior é limpa se não pertencer ao tipo (despesa vs receita).
- Categorias válidas: despesas em `GET /categories/`, receitas em `GET /income-categories/` (já existentes).
- Contas para o upload: `GET /accounts/`.

## 3. `agent_api` (chamado só pelo `finance_api`)

`POST /classify/transactions`
```json
// request
{
  "transactions": [
    {"id": "…", "merchant": "AUGUSTS BURGE", "raw_title": "Débito de Cartão",
     "raw_description": "PAYGO*AUGUSTS BURGE Uberlandia BRA. Cartão 1633",
     "direction": "OUT", "amount": 79.97}
  ],
  "expense_categories": [{"key": "comer_fora", "display_name": "Comer fora"}],
  "income_categories":  [{"key": "salario", "display_name": "Salário"}]
}
// response
{ "suggestions": [ {"id": "…", "category": "comer_fora", "confidence": 0.9} ] }
```
- `category` deve ser uma das chaves da lista correspondente à `direction` (`OUT` → despesas, `IN` → receitas); caso contrário `null`.
- `category: null` quando não houver evidência (ex.: nome de pessoa física).
- `confidence` ∈ [0,1].
- Erro do LLM → HTTP 5xx; o `finance_api` trata e segue sem IA.
