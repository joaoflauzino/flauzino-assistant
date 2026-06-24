# Lista de Próximos Passos (TODO)

## 1. Gastos Programados e Parcelamentos
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

## 2. Fechamento de Faturas e Dashboards
- [ ] Atualizar o esquema de "Métodos de Pagamento" / "Cartões" para incluir a data de fechamento e data de vencimento.
- [ ] Lidar com variações da **data de fechamento** (ex: dias não úteis), permitindo que o sistema tenha uma "prévia" configurada e a opção de alterar a data manualmente no fim do mês para uma visão 100% certeira.
- [ ] Ajustar as consultas da `finance_api` para que a visualização de gastos de um "mês fechado" seja **sempre** o intervalo entre a data de fechamento do mês anterior e a data de fechamento do mês atual.
- [ ] Atualizar o `frontend` para exibir os dashboards baseados nessas faturas e faturamentos dinâmicos, e não apenas no mês civil.

## 3. Consulta de Saldo e Limites por Categoria
- [ ] **Síncrono (Comandos e Texto):** Criar comandos no Telegram (ex: `/limites` ou `/saldo`) e **também habilitar a consulta por texto livre** via Agente (ex: "quanto ainda posso gastar de mercado?").
- [ ] **Assíncrono:** Configurar um *cron job* ou serviço agendado (ex: toda sexta-feira) para enviar proativamente uma mensagem ao Telegram resumindo a saúde financeira e os limites.

## 4. Geração de Gráficos sob Demanda (Integração com MCP)
- [ ] Implementar um servidor MCP (Model Context Protocol) capaz de consultar a `finance_api` e desenhar gráficos (ex: bibliotecas de plotagem).
- [ ] Integrar esse servidor para que o assistente (Agent) consiga gerar visualizações de gastos e enviá-las ao Telegram em formato de imagem **tanto via comandos quanto por texto natural** ("Gere um gráfico de pizza dos gastos desse mês").

## 5. Fluxo de Handlers (Refatoração para os Itens 3 e 4)
- [ ] Desenhar a arquitetura de Handlers no `telegram_api` para acomodar as novas intenções.
- [ ] **Garantir suporte total a Linguagem Natural e Áudio:** Além dos comandos (ex: `/limites`), o bot deve permitir que o usuário cadastre gastos, consulte saldos e solicite gráficos conversando normalmente, seja por texto ou enviando áudios.
- [ ] Avaliar como o Agente de IA tomará decisões com base nessa linguagem livre ("Como estão meus gastos?") para escolher a ferramenta certa (MCP de gráficos vs. API de saldo), mantendo o código limpo e a responsabilidade clara.

## 6. Limpeza e Retenção de Dados (Data Retention)
- [ ] Criar uma rotina agendada (ex: cron job diário ou script via Makefile) para limpar registros antigos do banco de dados (ex: gastos, recibos e áudios com mais de 2 anos).
- [ ] Garantir que essa limpeza mantenha as faturas em aberto e apenas delete o histórico antigo seguro, evitando o acúmulo de dados desnecessários e protegendo o cartão de memória do Raspberry Pi contra lotação.

## 7. Infraestrutura e Backups
- [ ] Descobrir porque o crontab com o backup do postgres não está executando todo dia as 03 da manhã.

## 8. Processamento de Áudio e Recibos (OCR)
- [ ] **Evolução do OCR:** Remover a dependência do *Tesseract*. Como você já usa a API do Gemini, vamos usar a capacidade **Multimodal do Gemini 2.5 Flash** dentro do `agent_api`. Ele lê a foto do recibo com perfeição e devolve os campos (valor, local, data) já estruturados em JSON, acabando com a dor de cabeça do OCR tradicional!
- [ ] **Armazenamento:** Salvar a imagem original do comprovante (em base64 ou num bucket/storage local) vinculado ao registro no banco de dados da `finance_api`.
- [ ] **Integração:** Revisar as rotas atuais de `/ocr/process-receipt` e `/audio/process-audio` no `agent_api` para unificá-las no novo fluxo do assistente.
