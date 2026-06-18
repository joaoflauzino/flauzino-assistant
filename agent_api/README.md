# Agent API

Interface de conversação para interagir com o sistema.

#### Enviar Mensagem (POST /chat)

```bash
curl -X 'POST' \
  'http://localhost:8001/chat' \
  -H 'Content-Type: application/json' \
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

