# Telegram Bot

Bot do Telegram inteligente e assíncrono para o ecossistema **Flauzino Assistant**. Oferece uma interface conversacional e ágil para registro de gastos diários, leitura de notas fiscais via OCR, transcrição de áudios e acompanhamento visual do orçamento.

---

## Funcionalidades

### 1. Registro Guiado de Gastos (`/gasto`)
- Fluxo conversacional interativo via `ConversationHandler`.
- Seleção através de botões inline com dados dinâmicos da `Finance API` (categorias, formas de pagamento e donos do cartão).
- Entrada de texto validada para valor, descrição do item e local da compra.
- Comunicação direta com a `Finance API` (`POST /spents`), garantindo respostas instantâneas sem depender de LLM.

### 2. Consulta Gráfica de Saldos e Limites (`/saldo` ou `/limites`)
- Teclado interativo com alternância de seleção de categorias (com botões "Todas" e "Nenhuma").
- Coleta os saldos na `Finance API` e solicita a renderização visual à `Graph API`.
- Responde com a imagem do gráfico gerado diretamente no chat.

### 3. Leitura de Cupons Fiscais e Recibos (OCR)
- Ao receber fotos de recibos/comprovantes, encaminha o arquivo para a `Agent API` (`POST /ocr/process-receipt`).
- Extrai texto e valores via Tesseract OCR e orienta o usuário sobre eventuais dados pendentes.

### 4. Áudio e Mensagens de Voz
- Suporta mensagens de voz e áudios (`.ogg`, `.mp3`, etc.).
- Encaminha o áudio para a `Agent API` (`POST /audio/process-audio`) para transcrição e extração automática dos dados do gasto.

### 5. Conversação Livre (IA)
- Qualquer mensagem de texto livre (ex.: _"quanto ainda posso gastar em alimentação este mês?"_) é enviada para a `Agent API` (`POST /chat`), que consulta e opera os dados com suporte a histórico de sessão.

### 6. Resumo Semanal Automático
- Rotina periódica via `JobQueue` executada todas as sextas-feiras às 10:00 (horário de Brasília).
- Envia automaticamente o gráfico de saldos atualizado para todos os usuários cadastrados na base.

### 7. Controle de Acesso e Segurança
- Middleware embutido que verifica o `@username` do Telegram contra a lista autorizada em `ALLOWED_TELEGRAM_USERNAMES`. Usuários não autorizados são bloqueados imediatamente.

### 8. Rastreabilidade e Correlation ID (`X-Request-ID`)
- O bot inicia o rastreamento distribuído gerando um identificador de correlação único (`UUIDv4`) para cada interação recebida (texto, áudio, foto ou comando).
- O `X-Request-ID` é injetado no contexto de logging e enviado em todas as chamadas HTTP para `agent_api` e `finance_api`, permitindo rastrear o ciclo de vida completo de cada solicitação nos logs da stack.

---

## Comandos Disponíveis

| Comando | Descrição |
|:---|:---|
| `/start` | Mensagem de boas-vindas e introdução ao bot |
| `/help` | Guia com exemplos práticos de uso e comandos |
| `/gasto` | Inicia o fluxo interativo passo a passo para registrar um gasto |
| `/saldo` | Abre o seletor de categorias para gerar o gráfico de saldo e gastos |
| `/limites` | Abre o seletor para visualização dos limites cadastrados |
| `/cancel` | Cancela o fluxo interativo ativo a qualquer momento |

---

## Variáveis de Ambiente

O serviço depende das seguintes variáveis no arquivo `.env`:

```env
TELEGRAM_BOT_TOKEN="seu_token_aqui"
ALLOWED_TELEGRAM_USERNAMES="usuario1,usuario2"
FINANCE_SERVICE_URL="http://localhost:8000"
AGENT_API_URL="http://localhost:8001"
GRAPH_SERVICE_URL="http://localhost:8002"
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/assistant"
```

---

## Como Executar

### Localmente
Certifique-se de que o banco de dados e os serviços necessários (`finance_api`, `agent_api`, `graph_api`) estejam ativos.

```bash
make run-telegram
# ou
uv run python -m telegram_api.main
```

### Docker
O bot é gerenciado via Docker Compose:
```bash
docker-compose -f infra/docker-compose.yml up -d telegram_bot
```

---

## Testes

```bash
uv run pytest telegram_api/tests
```
