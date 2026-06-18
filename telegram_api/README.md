# Telegram Bot

O Flauzino Assistant inclui um bot do Telegram que permite registrar gastos e processar recibos diretamente pelo aplicativo de mensagens.

### Como Usar
    
Certifique-se de que o serviços estão rodando conforme descrito na seção "Executando os Serviços".

1. **Encontre seu bot:**
   - Procure pelo username que você definiu no BotFather.
   - Envie `/start` para iniciar.

### Comandos Disponíveis

- `/start` - Mensagem de boas-vindas e instruções
- `/help` - Mostra como usar o bot com exemplos

### Como Usar

**Registrar gastos via mensagem de texto:**
```
gastei 50 reais no mercado com o cartão do itau do joao lucas
```

O bot irá:
1. Processar sua mensagem
2. Pedir informações faltantes (se houver)
3. Confirmar os dados antes de registrar
4. Salvar no banco de dados via `agent_api` → `finance_api`

**Enviar recibos via foto:**
1. Tire uma foto do recibo
2. Envie a foto para o bot
3. O bot irá extrair o texto automaticamente (OCR)
4. Pedir informações adicionais se necessário
5. Confirmar e registrar o gasto

**Enviar mensagens de áudio/voz:**
1. Grave uma mensagem de voz ou envie um arquivo de áudio pelo Telegram
2. O agente transcreverá sua voz e entenderá o gasto de forma nativa
3. Pedirá informações adicionais (por texto) se faltar algum detalhe
4. Você pode continuar respondendo com novos áudios ou textos (tudo flui na mesma sessão)
5. Confirmará e registrará o gasto

### Sessões de Conversa

- Cada chat do Telegram tem sua própria sessão
- O bot lembra do contexto da conversa
- Você pode corrigir ou adicionar informações a qualquer momento
- Todas as sessões são armazenadas no banco de dados

