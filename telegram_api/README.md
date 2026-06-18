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

*(Nota: O registro de gastos via texto livre foi temporariamente desativado a favor do fluxo interativo. Se você enviar apenas texto sem usar o comando `/gasto`, o bot listará os comandos disponíveis).*

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

- As sessões de fotos e áudios mantêm contexto no banco de dados.
- O fluxo de `/gasto` mantém o contexto em memória durante as etapas (Conversation Handler).

