# Frontend

Interface Web moderna construída com **React 19**, **TypeScript** e **Vite** para controle, acompanhamento visual e gerenciamento orçamentário no **Flauzino Assistant**.

---

## Funcionalidades e Telas

- **Dashboard**: Painel consolidado com indicadores financeiros, status dos limites do mês corrente e gráficos interativos de gastos vs. saldos disponíveis.
- **Gastos (`/spents`)**: Listagem detalhada e paginada de todas as despesas cadastradas, com filtros por data e categoria, além de suporte completo a criação, edição e exclusão.
- **Limites (`/limits`)**: Definição de limites mensais por categoria de gasto com barras visuais de progresso de consumo.
- **Categorias (`/categories`)**: Cadastro e personalização de categorias dinâmicas (nome de exibição e chave única).
- **Formas de Pagamento (`/payment-methods`)**: Gerenciamento de cartões de crédito/débito e contas bancárias.
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
