from telegram import Update
from telegram.ext import ContextTypes

from telegram_api.core.logger import get_logger

logger = get_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    welcome_message = (
        "👋 Olá! Sou o assistente financeiro da Família Flauzino.\n\n"
        "Você pode:\n"
        "• Enviar mensagens sobre seus gastos (ex: 'gastei 50 reais no mercado')\n"
        "• Enviar fotos de recibos para extração automática\n"
        "• Cadastrar limites de gastos\n\n"
        "Use /help para mais informações!"
    )

    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_message = (
        "📋 *Como usar o bot:*\n\n"
        "*Registrar gastos:*\n"
        "Envie uma mensagem descrevendo seu gasto. O bot vai te guiar para completar as informações:\n"
        "• Categoria\n"
        "• Valor\n"
        "• Item comprado\n"
        "• Método de pagamento\n"
        "• Proprietário do cartão\n"
        "• Local da compra\n\n"
        '_Exemplo:_ "gastei 50 reais no mercado com o cartão do itau do joao lucas"\n\n'
        "*Enviar recibos:*\n"
        "Envie uma foto do recibo e o bot irá extrair as informações automaticamente.\n\n"
        "*Cadastrar limites:*\n"
        "Diga quanto quer limitar os gastos em uma categoria.\n"
        '_Exemplo:_ "quero cadastrar um limite de 2000 reais para comer fora"\n\n'
        "💬 Cada conversa mantém seu contexto, então você pode corrigir ou adicionar informações a qualquer momento!"
    )

    logger.info(f"User {update.effective_user.id} requested help")
    await update.message.reply_text(help_message, parse_mode="Markdown")
