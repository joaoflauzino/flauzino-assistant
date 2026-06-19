# Lista de Próximos Passos (TODO)

## 1. Gastos Programados e Parcelamentos
- [ ] Criar modelo/tabela na `finance_api` para suportar gastos recorrentes e parcelados.
- [ ] Implementar endpoint para registrar compras parceladas (dividindo o valor total em parcelas com meses subsequentes).
- [ ] Ajustar o `telegram_api` para perguntar (se aplicável) em quantas vezes a compra foi feita ao registrar um gasto.

## 2. Fechamento de Faturas e Dashboards
- [ ] Atualizar o esquema de "Métodos de Pagamento" / "Cartões" para incluir a data de fechamento e data de vencimento.
- [ ] Ajustar as consultas da `finance_api` para que a visualização de gastos "do mês" possa ser filtrada pela janela de fechamento de cada cartão.
- [ ] Atualizar o `frontend` para exibir os dashboards baseados nas faturas dos cartões, e não apenas no mês civil.

## 3. Consulta de Saldo e Limites por Categoria
- [ ] **Síncrono (Comandos e Texto):** Criar comandos no Telegram (ex: `/limites` ou `/saldo`) e **também habilitar a consulta por texto livre** via Agente (ex: "quanto ainda posso gastar de mercado?").
- [ ] **Assíncrono:** Configurar um *cron job* ou serviço agendado (ex: toda sexta-feira) para enviar proativamente uma mensagem ao Telegram resumindo a saúde financeira e os limites.

## 4. Geração de Gráficos sob Demanda (Integração com MCP)
- [ ] Implementar um servidor MCP (Model Context Protocol) capaz de consultar a `finance_api` e desenhar gráficos (ex: bibliotecas de plotagem).
- [ ] Integrar esse servidor para que o assistente (Agent) consiga gerar visualizações de gastos e enviá-las ao Telegram em formato de imagem **tanto via comandos quanto por texto natural** ("Gere um gráfico de pizza dos gastos desse mês").

## 5. Fluxo de Handlers (Refatoração para os Itens 3 e 4)
- [ ] Desenhar a arquitetura de Handlers no `telegram_api` para acomodar as novas intenções (comandos e texto livre).
- [ ] Avaliar como o Agente de IA lidará com requisições de texto livre ("Como estão meus gastos?") para decidir entre acionar o MCP de gráficos ou apenas consultar a API de saldo, mantendo a responsabilidade clara entre o bot e o Agente.

## 6. Limpeza e Retenção de Dados (Data Retention)
- [ ] Criar uma rotina agendada (ex: cron job diário ou script via Makefile) para limpar registros antigos do banco de dados (ex: gastos, recibos e áudios com mais de 2 anos).
- [ ] Garantir que essa limpeza mantenha as faturas em aberto e apenas delete o histórico antigo seguro, evitando o acúmulo de dados desnecessários e protegendo o cartão de memória do Raspberry Pi contra lotação.
