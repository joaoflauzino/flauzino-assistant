# Frontend

Interface Web moderna construída com **React 19**, **TypeScript** e **Vite** para controle, acompanhamento visual e gerenciamento orçamentário no **Flauzino Assistant**.

---

## Funcionalidades e Telas

- **Dashboard (`/`)**: Painel consolidado com balanço de receitas vs. despesas, filtros rápidos por período (mês civil, faturas e customizado), filtros independentes e dinâmicos para **Contas Bancárias** e **Cartões de Crédito** (exibidos apenas quando houver dados correspondentes) e gráfico de **Top Gastos por Cartão**.
- **Importações (`/imports`)**: Esteira completa de importação de extratos bancários (arquivos CSV do C6 Bank). Oferece upload com seleção de conta, fila de revisão de transações em staging com sugestão assistida por IA/regras, edição em linha de categoria e local, vinculação de possíveis duplicatas e efetivação em lote.
- **Gastos (`/spents`)**: Listagem paginada de despesas com atalhos de período (*Mês Atual*, *Últimos 90 dias*, *Ver Todos*), filtros por data/categoria e suporte a criação, edição e exclusão.
- **Receitas (`/incomes`)**: Acompanhamento e registro de entradas financeiras (salários, rendimentos, prêmios) com atalhos de período e categorias de receita.
- **Contas Bancárias (`/accounts`)**: Cadastro e visualização de contas correntes, carteiras e investimentos por titular.
- **Cartões de Crédito (`/credit-cards`)**: Gestão de cartões vinculados a contas com controle de limites, datas de fechamento e vencimento.
- **Limites (`/limits`)**: Definição de limites mensais por categoria de gasto com barras visuais de progresso de consumo.
- **Categorias (`/categories` e `/income-categories`)**: Cadastro e personalização de categorias dinâmicas de despesas e receitas.
- **Faturas (`/invoices`) e Parcelamentos (`/installments`)**: Acompanhamento de faturas de cartão e parcelamentos em andamento.
- **Assinaturas (`/subscriptions`)**: Gestão de custos fixos e serviços recorrentes.

---

## Stack Tecnológica

- **Framework:** [React 19](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **Build Tool:** [Vite](https://vitejs.dev/)
- **Roteamento:** [React Router 7](https://reactrouter.com/)
- **Visualização de Dados:** [Chart.js](https://www.chartjs.org/) + `react-chartjs-2`
- **Ícones:** [Lucide React](https://lucide.dev/)
- **Comunicação HTTP:** [Axios](https://axios-http.com/)
- **Produção / Deploy:** [Nginx](https://nginx.org/) em container Docker com configuração de proxy reverso

---

## Como Executar

### 1. Desenvolvimento Local

Certifique-se de que a `Finance API` esteja ativa na porta 8000.

```bash
# Na raiz do projeto:
make run-frontend

# Ou dentro do diretório frontend/:
cd frontend
npm install
npm run dev
```

A aplicação estará disponível em `http://localhost:5173`.

### 2. Build de Produção

```bash
cd frontend
npm run build
```

Os arquivos estáticos compilados serão gerados no diretório `frontend/dist/`.

### 3. Docker

O frontend possui um `Dockerfile` multi-stage que compila o bundle e o serve através do Nginx:

```bash
docker-compose -f infra/docker-compose.yml up -d frontend
```
