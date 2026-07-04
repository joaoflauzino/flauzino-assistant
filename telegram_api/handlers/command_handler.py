from telegram import Update
from telegram.ext import ContextTypes

from telegram_api.core.logger import get_logger

logger = get_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    welcome_message = (
        "👋 Olá! Sou o assistente financeiro da Família Flauzino.\n\n"
        "Você pode:\n"
        "• Registrar gastos usando o comando /gasto de forma interativa\n"
        "• Consultar limites e saldos usando os comandos /limites ou /saldo\n"
        "• Mandar mensagens de texto/áudio como 'quanto posso gastar no mercado?'\n\n"
        "Use /help para mais informações!"
    )

    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_message = (
        "📋 *Como usar o bot:*\n\n"
        "*Registrar gastos (Guiado):*\n"
        "Envie o comando /gasto. O bot vai te guiar passo a passo com botões para completar as informações:\n"
        "• Categoria\n"
        "• Valor\n"
        "• Item comprado\n"
        "• Método de pagamento\n"
        "• Local da compra\n\n"
        "*Consultas de Saldo e Limites:*\n"
        "• Envie /saldo ou /limites para receber um relatório completo de todos os seus limites e gastos do mês com base no fechamento das faturas.\n\n"
        "*Consultas e Registros Livres (IA):*\n"
        "Você também pode conversar naturalmente comigo enviando texto ou áudio! Eu consigo entender o que você quer fazer.\n"
        "Exemplos do que você pode me mandar:\n"
        '- _"Quanto ainda tenho de mercado?"_\n'
        '- _"Comprei um lanche no McDonald\'s por 45 reais no cartão nubank"_\n'
        '- _"Cadastre um limite de 1000 reais para a categoria lazer"_\n'
    )

    logger.info(f"User {update.effective_user.id} requested help")
    await update.message.reply_text(help_message, parse_mode="Markdown")
