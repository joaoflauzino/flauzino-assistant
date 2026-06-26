# Item 2 - Fechamento de Faturas e Dashboards Dinâmicos

Este documento detalha o plano de implementação para o item 2 do arquivo TODO.md: "Fechamento de Faturas e Dashboards". O objetivo é evoluir o sistema de métodos de pagamento para suportar o conceito de "Fatura" de cartão de crédito, que não respeita necessariamente o mês civil e sim datas de fechamento e vencimento customizáveis e dinâmicas.

## Esclarecimento de Dúvidas e Exemplos

**1. Exemplo prático da tabela de Ciclos (Invoices):**
Imagine que você tem o **Cartão Nubank** com dia padrão de fechamento = 25.
1. O sistema cria automaticamente a Fatura de **Outubro/2026**.
2. Pelo padrão, ela fecharia no dia **25/10/2026** (essa é a "prévia").
3. Tudo que você passar no cartão entre 26/09 e 25/10 cai na Fatura de Outubro.
4. **A solução de ajuste manual:** Se por qualquer motivo o banco agir diferente, você vai na tela "Faturas", seleciona o Cartão Nubank para Outubro e muda a Data de Fechamento Real, o dashboard automaticamente reprocessa tudo.

**Automação para Pular Finais de Semana e Feriados:**
No backend, ao gerar a data prevista (ex: 25/10), o nosso serviço usará a biblioteca `holidays` (para feriados brasileiros) e verificará o dia da semana. Se o dia cair em um Sábado, Domingo ou Feriado Nacional, **o sistema postergará a data de fechamento automaticamente para o próximo dia útil** (conforme sua solicitação e o funcionamento dos seus cartões). 

**2. Como funcionará o Dashboard com múltiplos cartões?**
**Sim, você conseguirá visualizar TODOS os cartões juntos no Dashboard, cada um respeitando sua própria data.**
Quando você acessar o Dashboard e selecionar o **Mês de Junho**:
O Backend fará uma consulta inteligente que monta o "Junho" de cada método de pagamento separadamente:
- **Pix/Débito:** Pega os gastos de `01/06 a 30/06`.
- **Cartão Nubank (Fecha dia 25):** Pega os gastos de `26/05 a 25/06` (pois essa é a Fatura de Junho dele).
- **Cartão Itaú (Fecha dia 15):** Pega os gastos de `16/05 a 15/06` (pois essa é a Fatura de Junho dele).
Em seguida, ele soma tudo em um único Dashboard.

**Alternando entre "Visão de Faturas" e "Visão de Mês Civil":**
Para não perdermos a funcionalidade de "O que eu gastei entre 1 e 30?", eu adicionarei no topo do Dashboard do frontend um "Switch/Toggle" (botão de ligar/desligar).
- **Modo Mês Civil:** Exibe exatamente como é hoje. Ignora as faturas e puxa tudo de 01/06 a 30/06, de todos os cartões, de forma puramente cronológica.
- **Modo Faturas:** Aplica a nova lógica inteligente de fechamento dinâmico.

---

## Proposed Changes

### `finance_api` Models and Schemas

Nesta camada vamos criar a infraestrutura no banco de dados para suportar as faturas.

#### [MODIFY] `finance_api/models/payment_methods.py`
Adicionar campos para representar o comportamento de um cartão de crédito:
- `is_credit_card` (Boolean, default=False)
- `closing_day` (Integer, nullable=True): Ex: 25
- `due_day` (Integer, nullable=True): Ex: 5

#### [NEW] `finance_api/models/invoices.py`
Criar a entidade que representa um ciclo de fatura instanciado de um cartão num dado mês:
- `id` (UUID)
- `payment_method_key` (String, ForeignKey)
- `reference_month` (String formatada "YYYY-MM")
- `real_closing_date` (Date)
- `real_due_date` (Date)
- `status` (Enum: OPEN, CLOSED, PAID)

#### [MODIFY] `finance_api/schemas/payment_methods.py`
Atualizar os schemas do pydantic para validar os novos campos na criação e atualização dos métodos de pagamento.

#### [NEW] `finance_api/schemas/invoices.py`
Schemas para listar, atualizar (a data de fechamento/status) e retornar as Faturas (Invoices).

---

### `finance_api` Repositories, Services e Routers

A lógica de negócios para construir e ler as faturas, bem como como os gastos vão ser agregados.

#### [NEW] `finance_api/repositories/invoices.py` & `finance_api/services/invoices.py`
- Adicionar biblioteca `holidays` no requirements do backend.
- O serviço será inteligente: ao instanciar a data do ciclo baseada no `closing_day` e no mês atual, ele validará se o dia cai no final de semana ou feriado e **postergará para o próximo dia útil**.
- Também será capaz de retornar a fatura alterada manualmente se ela existir no banco.

#### [NEW] `finance_api/routers/invoices.py`
Expor endpoints:
- `GET /invoices` (Lista as faturas por mês/cartão)
- `PUT /invoices/{invoice_id}/closing-date` (Permite alterar data de fechamento manualmente)

#### [MODIFY] `finance_api/routers/spents.py` & `finance_api/repositories/spents.py`
Criar o endpoint `GET /spents/dashboard`. Ele aceitará os seguintes parâmetros:
- `reference_month` (ex: "2026-06")
- `mode` (Enum: "CIVIL_MONTH" ou "INVOICES").
Dependendo do modo, a query varre os gastos puxando as datas cronológicas simples (CIVIL_MONTH) ou fazendo a agregação dinâmica por faturas de cartões (INVOICES).

---

### `frontend` Interface

O painel de controle receberá novas telas e modificações nas tabelas para habilitar as datas das faturas.

#### [MODIFY] `frontend/src/pages/PaymentMethodsPage.tsx`
- No formulário de adicionar/editar um método de pagamento, incluir um checkbox "É um cartão de crédito?".
- Se marcado, exibir os campos "Dia de Fechamento" e "Dia de Vencimento".

#### [NEW] `frontend/src/pages/InvoicesPage.tsx`
- Uma nova página chamada "Faturas".
- Vai listar todos os cartões cadastrados e suas datas de fechamento previstas/reais (já mostrando os ajustes automáticos de postergar para dias úteis), com um botão "Ajustar Data", permitindo override manual.

#### [MODIFY] `frontend/src/pages/Dashboard.tsx`
- No topo da página (ao lado de escolher o mês), teremos um "Toggle/Switch" para **Visão: Faturas** ou **Visão: Mês Civil**.
- As requisições passarão o `mode` para o backend para trazer o dashboard customizado.
