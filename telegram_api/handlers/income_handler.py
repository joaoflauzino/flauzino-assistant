import warnings

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.warnings import PTBUserWarning

from telegram_api.core.correlation import set_request_id
from telegram_api.core.http_client import (
    get_valid_income_categories,
    get_valid_payment_methods,
    save_income,
)
from telegram_api.core.logger import get_logger

logger = get_logger(__name__)

(
    SELECT_CATEGORY,
    TYPE_DESCRIPTION,
    TYPE_VALUE,
    SELECT_PAYMENT_METHOD,
    CONFIRMATION,
) = range(5)


def build_inline_keyboard(options: list[str], columns: int = 2) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for option in options:
        row.append(InlineKeyboardButton(option, callback_data=option))
        if len(row) == columns:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


async def receita_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the income registration flow."""
    set_request_id()
    logger.info(f"User {update.effective_user.id} started income registration flow")
    context.user_data["income"] = {}

    categories = await get_valid_income_categories()
    reply_markup = build_inline_keyboard(categories)

    await update.message.reply_text(
        "💰 *Vamos registrar uma nova receita!*\n\nQual é a categoria da entrada?",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return SELECT_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    context.user_data["income"]["category"] = query.data
    logger.info(f"Selected income category: {query.data}")

    await query.edit_message_text(
        text=f"Categoria selecionada: *{query.data}*\n\nQual é a descrição ou fonte da receita? (ex: 'Salário', 'Pix de cliente')",
        parse_mode="Markdown",
    )
    return TYPE_DESCRIPTION


async def type_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    context.user_data["income"]["description"] = text
    logger.info(f"Typed income description: {text}")

    await update.message.reply_text("Qual foi o valor recebido em R$?")
    return TYPE_VALUE


async def type_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    try:
        value = float(text.replace("R$", "").replace(" ", "").replace(",", "."))
        if value <= 0:
            raise ValueError()
        context.user_data["income"]["amount"] = value
    except ValueError:
        await update.message.reply_text(
            "Valor inválido. Por favor, digite um número positivo (ex: 1500.00 ou 1500,00)."
        )
        return TYPE_VALUE

    logger.info(f"Typed income value: {value}")

    payment_methods = await get_valid_payment_methods()
    methods_with_skip = payment_methods + ["Pular / Nenhuma"]
    reply_markup = build_inline_keyboard(methods_with_skip)

    await update.message.reply_text(
        "Em qual conta ou método esse valor foi recebido?",
        reply_markup=reply_markup,
    )
    return SELECT_PAYMENT_METHOD


async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    selected = query.data
    pm = None if selected == "Pular / Nenhuma" else selected
    context.user_data["income"]["payment_method"] = pm
    logger.info(f"Selected income payment method: {pm}")

    inc = context.user_data["income"]
    pm_display = pm if pm else "Não especificado"
    summary_msg = (
        f"📝 *Confirmação de Receita:*\n\n"
        f"• *Categoria:* {inc['category']}\n"
        f"• *Descrição:* {inc['description']}\n"
        f"• *Valor:* R$ {inc['amount']:,.2f}\n"
        f"• *Conta/Método:* {pm_display}\n\n"
        f"Deseja registrar essa entrada?"
    )

    confirm_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Confirmar", callback_data="confirm"),
                InlineKeyboardButton("❌ Cancelar", callback_data="cancel"),
            ]
        ]
    )

    await query.edit_message_text(
        text=summary_msg, reply_markup=confirm_keyboard, parse_mode="Markdown"
    )
    return CONFIRMATION


async def confirm_income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "confirm":
        inc = context.user_data.get("income", {})
        payload = {
            "category": inc.get("category"),
            "description": inc.get("description"),
            "amount": inc.get("amount"),
            "payment_method": inc.get("payment_method"),
        }
        try:
            await save_income(payload)
            await query.edit_message_text(
                "✅ *Receita registrada com sucesso no sistema financeiro!*",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Erro ao salvar receita: {e}")
            await query.edit_message_text(
                "❌ Ocorreu um erro ao salvar a receita. Tente novamente mais tarde."
            )
    else:
        await query.edit_message_text("Operação de receita cancelada.")

    context.user_data.pop("income", None)
    return ConversationHandler.END


async def cancel_income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("income", None)
    await update.message.reply_text("Registro de receita cancelado.")
    return ConversationHandler.END


with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=PTBUserWarning)
    income_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("receita", receita_command)],
        states={
            SELECT_CATEGORY: [CallbackQueryHandler(select_category)],
            TYPE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_description)],
            TYPE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_value)],
            SELECT_PAYMENT_METHOD: [CallbackQueryHandler(select_payment_method)],
            CONFIRMATION: [CallbackQueryHandler(confirm_income, pattern="^(confirm|cancel)$")],
        },
        fallbacks=[
            CommandHandler("cancelar", cancel_income),
            CommandHandler("cancel", cancel_income),
        ],
    )
