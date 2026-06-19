from telegram import Update
from telegram.ext import ContextTypes

from telegram_api.core.logger import get_logger

logger = get_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    welcome_message = (
        "👋 Olá! Sou o assistente financeiro da Família Flauzino.\n\n"
        "Você pode:\n"
        "• Registrar gastos usando o comando /gasto de forma interativa\n\n"
        "Use /help para mais informações!"
    )

    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_message = (
        "📋 *Como usar o bot:*\n\n"
        "*Registrar gastos:*\n"
        "Envie o comando /gasto. O bot vai te guiar passo a passo com botões para completar as informações:\n"
        "• Categoria\n"
        "• Valor\n"
        "• Item comprado\n"
        "• Método de pagamento\n"
        "• Proprietário do cartão\n"
        "• Local da compra\n\n"
        "💬 O registro de gastos via mensagem de texto livre foi temporariamente desativado a favor do fluxo interativo."
    )

    logger.info(f"User {update.effective_user.id} requested help")
    await update.message.reply_text(help_message, parse_mode="Markdown")
