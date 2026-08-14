# Flauzino Assistant — TODO (Melhorado)

> Versão reorganizada: as duas prioridades arquiteturais de **integração MCP** ficam no topo;
> o restante é o conteúdo histórico do TODO original, com os itens concluídos consolidados no final.

## 1. Refatoração MCP — Desacoplamento e Orquestração (PRIORIDADE)

**Objetivo:** cada serviço expõe suas capabilities via **MCP próprio**; o `agent_api` é o **cliente MCP orquestrador**; nenhum serviço chama o outro "por dentro" via HTTP.

Hoje o `mcp_server` busca dados da `finance_api` internamente (`services/finance_service.py`) para desenhar gráficos. A ideia é quebrar esse acoplamento:

- [ ] **`finance_api`: expor servidor MCP próprio** (Streamable HTTP) com tools de **dados** (saldo/limites por categoria, gastos, etc.). As rotas REST continuam existindo normalmente.
- [ ] **`mcp_server` → renomear para `graph_api`**: a tool de gráfico deixa de buscar dados e vira **função pura** — recebe os dados estruturados por parâmetro (categorias/valores/limites) e devolve a imagem (PNG). Remove `services/finance_service.py`. Não precisa conhecer a `finance_api`.
- [ ] **`agent_api`: cliente MCP dos dois + orquestração**: quando a LLM sinaliza intenção de gráfico, o `chat.py` encadeia de forma **determinística**: chama finance tool → pega o JSON → chama graph tool → devolve imagem. O dado não passa pela LLM (só por argumentos JSON entre tools).
- [ ] **Decisão de ferramenta por linguagem livre**: separar a lógica do agente para escolher entre finance MCP (saldo/limites/consulta) e graph MCP (gráficos), em vez da API de saldo REST.
- [ ] **Corrigir bug:** follow-up do histórico na geração de gráficos não está funcionando (item 5 antigo).
- [ ] Atualizar `scripts/test_mcp_isolated.py` e testes: graph tool vira função pura → testes sem mockar `finance_service`; adicionar testes do MCP da `finance_api`.

## 2. Dupla interface por serviço — MCP **e** HTTP (PRIORIDADE)

**Objetivo:** cada API (`finance_api`, `graph_api`) expõe os **mesmos dados/ações via dois canais**: REST puro e MCP. O consumidor escolhe o canal.

Padrão de referência já existente no `telegram_api`:
- **Comandos** (ex: `/limites`, `/saldo`) → HTTP normal (REST direto).
- **Texto livre / áudio** → `agent_api`, que decide e orquestra via MCP.

- [ ] Garantir que `finance_api` tenha rota REST para tudo o que expõe via MCP (cadastrar, consultar, listar).
- [ ] Garantir que `graph_api` tenha rota REST (`/graphs/balance` já existe) além das MCP tools.
- [ ] Documentar o padrão no `telegram_api`: comandos → REST; linguagem natural/áudio → `agent_api`.
- [ ] Frontend continua consumindo via REST (sem MCP).

---

## 3. Fluxo de Handlers no `telegram_api` (histórico)

- [ ] Desenhar a arquitetura de Handlers no `telegram_api` para acomodar as novas intenções.
- [ ] **Garantir suporte total a Linguagem Natural e Áudio:** além dos comandos (ex: `/limites`), o bot deve permitir que o usuário cadastre gastos, consulte saldos e solicite gráficos conversando normalmente, seja por texto ou enviando áudios.

## 4. Registro de Gastos (histórico)

- [ ] **Bug:** Durante o cadastro via `/gasto`, quando a LLM pede confirmação e exibe os botões (Confirmar/Cancelar), se o usuário digitar texto para corrigir algo ao invés de clicar, as próximas mensagens da LLM vêm sem formatação e ela perde o contexto, exigindo repetir todos os valores.

## 5. Processamento de Áudio e Recibos (OCR) (histórico)

- [ ] **Evolução do OCR:** Remover a dependência do *Tesseract*. Como já se usa a API do Gemini, usar a capacidade **Multimodal do Gemini 2.5 Flash** dentro do `agent_api`. Ele lê a foto do recibo com perfeição e devolve os campos (valor, local, data) já estruturados em JSON, acabando com a dor de cabeça do OCR tradicional!
- [ ] **Armazenamento:** Salvar a imagem original do comprovante (em base64 ou num bucket/storage local) vinculado ao registro no banco de dados da `finance_api`.
- [ ] **Integração:** Revisar as rotas atuais de `/ocr/process-receipt` e `/audio/process-audio` no `agent_api` para unificá-las no novo fluxo do assistente.

## 6. Limpeza e Retenção de Dados (Data Retention) (histórico)

- [ ] Criar uma rotina agendada (ex: cron job diário ou script via Makefile) para limpar registros antigos do banco de dados (ex: gastos, recibos e áudios com mais de 2 anos).
- [ ] Garantir que essa limpeza mantenha as faturas em aberto e apenas delete o histórico antigo seguro, evitando o acúmulo de dados desnecessários e protegendo o cartão de memória do Raspberry Pi contra lotação.

## 7. Infraestrutura e Backups (histórico)

- [ ] Descobrir porque o crontab com o backup do postgres não está executando todo dia as 03 da manhã.

---

## ✅ Concluído (histórico)

### Gastos Programados e Parcelamentos
- [x] Criar modelo/tabela na `finance_api` para suportar gastos recorrentes e parcelados.
- [x] Implementar endpoint para registrar compras parceladas (dividindo o valor total em parcelas com meses subsequentes).
- [x] Permitir o cadastro de **compras parceladas em andamento** (ex: cadastrar uma compra de 10x que já está na 5ª parcela).
- [x] Implementar suporte a **Assinaturas (Recorrência contínua)**: cadastrar serviços (ex: Amazon Prime, Netflix) com opção de ativar/desativar, diferentemente de parcelamentos que têm um fim pré-determinado.
- [x] Ajustar o `telegram_api` para perguntar (se aplicável) em quantas vezes a compra foi feita ao registrar um gasto, ou se é uma assinatura contínua.
- [x] Atualizar o `frontend` para listar assinaturas e visualizar adequadamente as compras parceladas no painel e na tela de gastos.
- [x] Mostrar número da parcela (`x/y`) ao lado do nome do gasto no painel do frontend para compras parceladas.
- [x] Transformar os campos de `Categoria`, `Método` e `Titular` em opções de seleção (dropdowns dinâmicos) nos formulários do Frontend.
- [x] Implementar fluxo no `telegram_api` para perguntar a data da compra (Hoje/Agora vs Data Específica), usando calendário interativo ou botões.
- [x] **Seção de Compras Parceladas**: Criar página no painel (Frontend) e rota agregada na API para listar o progresso de compras parceladas agrupadas por categoria, mostrando visualmente quantas parcelas faltam para acabar.

### Fechamento de Faturas e Dashboards
- [x] Atualizar o esquema de "Métodos de Pagamento" / "Cartões" para incluir a data de fechamento e data de vencimento (lembrando que cada cartão pode ter sua data de fechamento e data de vencimento).
- [x] Lidar com variações da **data de fechamento** (ex: dias não úteis), permitindo que o sistema tenha uma "prévia" configurada e a opção de alterar a data manualmente no fim do mês para uma visão 100% certeira.
- [x] Ajustar as consultas da `finance_api` para que a visualização de gastos de um "mês fechado" seja **sempre** o intervalo entre a data de fechamento do mês anterior e a data de fechamento do mês atual.
- [x] Atualizar o `frontend` para exibir os dashboards baseados nessas faturas e faturamentos dinâmicos, e não apenas no mês civil.
- [x] Adicionar filtro no Dashboard para permitir a seleção de um, múltiplos ou todos os cartões/métodos de pagamento.
- [x] Implementar um gráfico no Dashboard mostrando o gasto total por cartão de acordo com os filtros aplicados.

### Regras de Validação e Melhoria de Erros
- [x] Atualizar os cartões no `init.sql` para crédito e com datas de vencimento/fechamento.
- [x] Criar validação bloqueando a titular `lailla` de utilizar outro cartão que não seja `nubank`.
- [x] Configurar um interceptador de erros no frontend para exibir as validações da API claramente na interface.
- [x] Padronizar a funcionalidade de "Excluir" no frontend (demais seções) usando o Modal React, para ficar idêntico à seção de gastos.
- [x] Validar a criação de categorias na seção de categorias (frontend/backend) para impedir duplicidades de chaves que já existem.

### Consulta de Saldo e Limites por Categoria
- [x] **Síncrono (Comandos e Texto):** Criar comandos no Telegram (ex: `/limites` ou `/saldo`) e **também habilitar a consulta por texto livre** via Agente (ex: "quanto ainda posso gastar de mercado?").
- [x] Deixar de retornar texto em `/limites` e `/saldo` e passar a retornar gráficos.
- [x] **Assíncrono:** Configurar um *cron job* ou serviço agendado (ex: toda sexta-feira) para enviar proativamente uma mensagem ao Telegram resumindo a saúde financeira e os limites.
- [x] O campo de `mês referência` (reference_month) deve ser um seletor (dropdown/opções) e não um campo de texto livre, para evitar erros de formatação ao editar.

### Geração de Gráficos sob Demanda (Integração com MCP)
- [x] Implementar um servidor MCP (Model Context Protocol) capaz de consultar a `finance_api` e desenhar gráficos (ex: bibliotecas de plotagem).
- [x] Integrar esse servidor para que o assistente (Agent) consiga gerar visualizações de gastos e enviá-las ao Telegram em formato de imagem **tanto via comandos quanto por texto natural** ("Gere um gráfico de pizza dos gastos desse mês").

### Registro de Gastos
- [x] Ao registrar gastos com texto livre a IA não estava identificando corretamente os métodos de pagamento (Ex: "passei c6" → não existe; existe o `c6_joao`).
- [x] O CRUD (`finance_api`) não estava barrando métodos de pagamento na tabela de gastos que não existem na tabela de pagamentos (Ex: "passei c6" → não existe; existe o `c6_joao`).
