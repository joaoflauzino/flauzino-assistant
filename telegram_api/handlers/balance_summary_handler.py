from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from telegram_api.core.correlation import set_request_id
from telegram_api.core.http_client import get_monthly_balance_summary
from telegram_api.core.logger import get_logger

logger = get_logger(__name__)


def _format_currency(value: float) -> str:
    formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "+" if value > 0 else ("-" if value < 0 else "")
    return f"{sign}R$ {formatted}"


async def balanco_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /balanco command to show executive monthly cash flow."""
    set_request_id()
    logger.info(f"User {update.effective_user.id} requested monthly balance summary")

    args = context.args or []
    reference_month = args[0] if len(args) > 0 else None

    summary = await get_monthly_balance_summary(reference_month=reference_month)
    if not summary:
        await update.message.reply_text(
            "❌ Não foi possível carregar o resumo do balanço mensal no momento. Tente novamente mais tarde."
        )
        return

    ref_month = summary.get("reference_month", "Atual")
    total_incomes = summary.get("total_incomes", 0.0)
    total_spents = summary.get("total_spents", 0.0)
    net_balance = summary.get("net_balance", 0.0)
    is_positive = summary.get("is_positive", False)
    savings_rate = summary.get("savings_rate", 0.0)

    status_icon = "🟢" if is_positive else "🔴"
    status_label = "Superávit" if is_positive else "Déficit"

    msg = (
        f"📊 *Balanço Financeiro Integrado* (`{ref_month}`)\n\n"
        f"💰 *Receitas (Entradas):* {_format_currency(total_incomes)}\n"
        f"💸 *Despesas (Saídas):* {_format_currency(total_spents)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_icon} *Resultado Líquido:* {_format_currency(net_balance)} ({status_label})\n"
        f"📈 *Taxa de Economia:* {savings_rate:.1f}%\n"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


balanco_handler = CommandHandler("balanco", balanco_command)
