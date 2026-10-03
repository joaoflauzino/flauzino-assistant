from telegram import Update
from telegram.ext import ContextTypes

from telegram_api.core.logger import get_logger

logger = get_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    welcome_message = (
        "👋 Olá! Sou o assistente financeiro da Família Flauzino.\n\n"
        "Você pode:\n"
        "• Registrar despesas usando o comando /gasto de forma interativa\n"
        "• Registrar receitas usando o comando /receita de forma interativa\n"
        "• Ver o balanço mensal integrado usando o comando /balanco\n"
        "• Consultar limites e saldos de gastos usando /limites ou /saldo\n"
        "• Mandar mensagens de texto/áudio como 'quanto posso gastar no mercado?' ou 'registra salário de 5000'\n\n"
        "Use /help para mais informações!"
    )

    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_message = (
        "📋 *Como usar o bot:*\n\n"
        "*Registrar despesas (Guiado):*\n"
        "Envie o comando /gasto. O bot vai te guiar passo a passo para registrar uma despesa.\n\n"
        "*Registrar receitas (Guiado):*\n"
        "Envie o comando /receita. O bot vai te guiar passo a passo para registrar uma entrada financeira (salário, pix, etc.).\n\n"
        "*Balanço Mensal Integrado:*\n"
        "Envie /balanco para ver o resultado executivo do mês (Receitas vs Despesas, Saldo Líquido e Taxa de Economia).\n\n"
        "*Consultas de Saldo e Limites de Gastos:*\n"
        "• Envie /saldo ou /limites para receber um relatório completo por categoria de gastos.\n\n"
        "*Consultas e Registros Livres (IA):*\n"
        "Você também pode conversar naturalmente comigo enviando texto ou áudio! Exemplos:\n"
        '- _"Quanto ainda tenho de mercado?"_\n'
        '- _"Comprei um lanche no McDonald\'s por 45 reais no cartão nubank"_\n'
        '- _"Recebi meu salário de 5000 no Itaú"_\n'
        '- _"Fechei o mês no positivo?"_\n'
    )

    logger.info(f"User {update.effective_user.id} requested help")
    await update.message.reply_text(help_message, parse_mode="Markdown")
