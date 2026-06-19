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
- `/gasto` - Inicia o fluxo interativo passo a passo para registrar um gasto

### Como Usar

**Registrar gastos (Fluxo Interativo):**
1. Envie `/gasto` para o bot.
2. O bot guiará você com botões (para categorias, métodos de pagamento e donos) e com entrada de texto (para item, valor e local).
3. Confirme os dados e o bot registrará diretamente na API Financeira.

### Sessões de Conversa

- O fluxo de `/gasto` mantém o contexto em memória durante as etapas (Conversation Handler).

