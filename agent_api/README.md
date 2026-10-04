# Agent API

Interface de conversação inteligente para interagir com o ecossistema, combinando modelos LLM e OCR para processamento de linguagem natural, áudios e recibos.

---

## Rastreabilidade e Correlation ID (`X-Request-ID`)

A `agent_api` propaga identificadores de correlação para observabilidade fim a fim:
- **Middleware:** O `CorrelationIdMiddleware` captura o cabeçalho `X-Request-ID` da requisição HTTP (ou gera um novo UUIDv4 se ausente) e o injeta no contexto assíncrono.
- **Propagação Externa:** Todas as requisições HTTP feitas pela `agent_api` para a `Finance API` repassam automaticamente o cabeçalho `X-Request-ID`.
- **Logs:** Os registros de log da aplicação incluem o prefixo `[request_id]`, correlacionando todas as ações desencadeadas por uma mesma interação.
- **Resposta:** O cabeçalho `X-Request-ID` é retornado em todas as respostas HTTP da API.

---

#### Enviar Mensagem (POST /chat)

```bash
curl -X 'POST' \
  'http://localhost:8001/chat' \
  -H 'Content-Type: application/json' \
  -H 'X-Request-ID: opcional-uuid-de-correlacao' \
  -d '{
  "message": "gastei 50 reais no mercado com o cartão do itau do joao lucas",
  "session_id": "optional-uuid"
}'
```

#### Extrair Texto de Recibo (POST /ocr/extract)

Extrai texto de uma imagem de recibo usando OCR.

```bash
curl -X 'POST' \
  'http://localhost:8001/ocr/extract' \
  -F 'file=@/path/to/receipt.jpg'
```

**Resposta:**
```json
{
  "text": "SUPERMERCADO XYZ\nValor: R$ 132,07\n...",
  "confidence": 85.5,
  "char_count": 1235,
  "filename": "receipt.jpg"
}
```

#### Processar Recibo Completo (POST /ocr/process-receipt)

Processa uma imagem de recibo e inicia/continua uma sessão de chat.

```bash
curl -X 'POST' \
  'http://localhost:8001/ocr/process-receipt' \
  -F 'file=@/path/to/receipt.jpg'
```

**Resposta:**
```json
{
  "response": "Para registrar o gasto, preciso do método de pagamento utilizado (Itau, PicPay, XP, Nubank ou C6), quem foi o proprietário...",
  "session_id": "9a144f4c-016e-4792-936f-504fe524bf10",
  "history": [
    {
      "role": "user",
      "content": "Aqui está o texto extraído de um recibo...\n\nPor favor, extraia as informações de gastos."
    },
    {
      "role": "assistant",
      "content": "Para registrar o gasto, preciso do método de pagamento..."
    }
  ]
}
```

**Você pode então continuar a conversa usando o `/chat` com o `session_id` retornado:**

```bash
curl -X 'POST' \
  'http://localhost:8001/chat' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "foi com o cartão do itau do joao lucas",
    "session_id": "9a144f4c-016e-4792-936f-504fe524bf10"
  }'
```

**Formatos suportados:** JPG, JPEG, PNG, WebP, BMP, TIFF  
**Tamanho máximo:** 10MB

#### Processar Áudio (POST /audio/process-audio)

Processa um arquivo de áudio ou mensagem de voz transcrita e inicia/continua uma sessão de chat perfeitamente.

```bash
curl -X 'POST' \
  'http://localhost:8001/audio/process-audio' \
  -F 'file=@/path/to/audio.ogg'
```

**Resposta:**
```json
{
  "response": "Para registrar o gasto, preciso de quem foi o proprietário...",
  "session_id": "9a144f4c-016e-4792-936f-504fe524bf10",
  "history": [
    {
      "role": "user",
      "content": "Ontem eu almocei no restaurante X e paguei 35 reais no crédito do nubank da lailla"
    },
    {
      "role": "assistant",
      "content": "Para registrar o gasto, preciso de quem foi o proprietário..."
    }
  ]
}
```

**Formatos de Áudio suportados:** OGG, MP3, WAV, M4A, etc.  
**Tamanho máximo do Áudio:** 10MB

#### Classificar Transações em Lote com LLM (POST /classify/transactions)

Endpoint estruturado que recebe uma lista de transações bancárias pendentes de classificação (junto com a lista de categorias válidas de despesa e receita) e utiliza LLM com *structured output* para sugerir a categoria e o nível de confiança (0 a 1).

```bash
curl -X 'POST' \
  'http://localhost:8001/classify/transactions' \
  -H 'Content-Type: application/json' \
  -d '{
    "transactions": [
      {
        "id": "1",
        "merchant": "POSTO IPIRANGA",
        "raw_title": "Compra Cartao Debito POSTO IPIRANGA",
        "direction": "OUT",
        "amount": 150.00
      }
    ],
    "expense_categories": [
      { "key": "transporte", "display_name": "Transporte e Combustível" },
      { "key": "alimentacao", "display_name": "Alimentação" }
    ],
    "income_categories": [
      { "key": "salario", "display_name": "Salário" }
    ]
  }'
```

**Resposta:**
```json
{
  "classifications": [
    {
      "id": "1",
      "suggested_category": "transporte",
      "confidence": 0.95
    }
  ]
}
```
