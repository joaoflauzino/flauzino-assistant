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
from telegram_api.core.finance_client import get_valid_categories, get_valid_payment_methods
from telegram_api.core.logger import get_logger
from telegram_api.handlers.expense_confirmation import (
    ask_for_date,
    select_date_option,
    type_custom_date,
)
from telegram_api.handlers.expense_states import (
    CONFIRMATION,
    SELECT_CATEGORY,
    SELECT_DATE_OPTION,
    SELECT_PAYMENT_METHOD,
    SELECT_PURCHASE_TYPE,
    TYPE_CURRENT_INSTALLMENT,
    TYPE_CUSTOM_DATE,
    TYPE_ITEM_BOUGHT,
    TYPE_LOCATION,
    TYPE_TOTAL_INSTALLMENTS,
    TYPE_VALUE,
)
from telegram_api.services.expense import persist_expense

logger = get_logger(__name__)


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


async def gasto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the expense registration flow."""
    if update.effective_user is None or update.message is None or context.user_data is None:
        return ConversationHandler.END

    set_request_id()
    logger.info(f"User {update.effective_user.id} started expense registration flow")
    context.user_data["expense"] = {}

    categories = await get_valid_categories()
    reply_markup = build_inline_keyboard(categories)

    await update.message.reply_text(
        "Vamos registrar um novo gasto! \n\nQual a categoria?",
        reply_markup=reply_markup,
    )
    return SELECT_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None or context.user_data is None:
        return ConversationHandler.END

    await query.answer()

    context.user_data["expense"]["category"] = query.data
    logger.info(f"Selected category: {query.data}")

    await query.edit_message_text(
        text=f"Categoria selecionada: {query.data}\n\nO que você comprou?"
    )
    return TYPE_ITEM_BOUGHT


async def type_item_bought(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None or message.text is None or context.user_data is None:
        return ConversationHandler.END

    text = message.text
    context.user_data["expense"]["item_bought"] = text
    logger.info(f"Typed item bought: {text}")

    await message.reply_text("Qual foi o valor?")
    return TYPE_VALUE


async def type_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None or message.text is None or context.user_data is None:
        return ConversationHandler.END

    text = message.text
    try:
        value = float(text.replace(",", "."))
        context.user_data["expense"]["amount"] = value
    except ValueError:
        await message.reply_text(
            "Valor inválido. Por favor, digite um número (ex: 50.00 ou 50,00)."
        )
        return TYPE_VALUE

    logger.info(f"Typed value: {value}")

    payment_methods = await get_valid_payment_methods()
    reply_markup = build_inline_keyboard(payment_methods)

    await message.reply_text(
        "Qual foi o método de pagamento?",
        reply_markup=reply_markup,
    )
    return SELECT_PAYMENT_METHOD


async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None or context.user_data is None:
        return ConversationHandler.END

    await query.answer()

    context.user_data["expense"]["payment_method"] = query.data
    logger.info(f"Selected payment method: {query.data}")

    await query.edit_message_text(
        text=f"Método de pagamento: {query.data}\n\nOnde foi a compra? (Local)"
    )
    return TYPE_LOCATION


async def type_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None or message.text is None or context.user_data is None:
        return ConversationHandler.END

    text = message.text
    context.user_data["expense"]["location"] = text
    logger.info(f"Typed location: {text}")

    keyboard = [
        [
            InlineKeyboardButton("À vista", callback_data="a_vista"),
            InlineKeyboardButton("Parcelada", callback_data="parcelada"),
            InlineKeyboardButton("Assinatura", callback_data="assinatura"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text("Qual o tipo dessa despesa?", reply_markup=reply_markup)
    return SELECT_PURCHASE_TYPE


async def select_purchase_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None or context.user_data is None:
        return ConversationHandler.END

    await query.answer()

    purchase_type = query.data
    context.user_data["expense"]["purchase_type"] = purchase_type
    logger.info(f"Selected purchase type: {purchase_type}")

    if purchase_type == "parcelada":
        await query.edit_message_text(text="Em quantas vezes foi dividido? (Ex: 10)")
        return TYPE_TOTAL_INSTALLMENTS

    return await ask_for_date(query, context)


async def type_total_installments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None or message.text is None or context.user_data is None:
        return ConversationHandler.END

    text = message.text
    try:
        total = int(text)
        if total < 2:
            raise ValueError()
        context.user_data["expense"]["total_installments"] = total
    except ValueError:
        await message.reply_text("Por favor, digite um número inteiro maior que 1.")
        return TYPE_TOTAL_INSTALLMENTS

    await message.reply_text(
        "Essa é a parcela de número X? (Ex: 1 se for nova, 5 se for uma compra em andamento)"
    )
    return TYPE_CURRENT_INSTALLMENT


async def type_current_installment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None or message.text is None or context.user_data is None:
        return ConversationHandler.END

    text = message.text
    total = context.user_data["expense"]["total_installments"]
    try:
        current = int(text)
        if current < 1 or current > total:
            raise ValueError()
        context.user_data["expense"]["current_installment"] = current
    except ValueError:
        await message.reply_text(f"Por favor, digite um número entre 1 e {total}.")
        return TYPE_CURRENT_INSTALLMENT

    return await ask_for_date(message, context)


async def confirm_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None or context.user_data is None:
        return ConversationHandler.END

    await query.answer()

    if query.data == "confirm":
        try:
            await persist_expense(context.user_data.get("expense", {}))
            await query.edit_message_text(text="✅ Registro salvo com sucesso!")
            logger.info("Saved successfully.")
        except Exception as error:  # Boundary: report save failures back to the user.
            logger.error(f"Failed to save: {error}")
            await query.edit_message_text(
                text="❌ Ocorreu um erro ao salvar. Tente novamente mais tarde."
            )
    else:
        await query.edit_message_text(text="❌ Registro cancelado.")
        logger.info("Registration cancelled.")

    context.user_data.pop("expense", None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    message = update.message
    if message is None or context.user_data is None:
        return ConversationHandler.END

    await message.reply_text("Registro cancelado.")
    context.user_data.pop("expense", None)
    return ConversationHandler.END


with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=PTBUserWarning)
    expense_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gasto", gasto_command)],
        states={
            SELECT_CATEGORY: [CallbackQueryHandler(select_category)],
            TYPE_ITEM_BOUGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_item_bought)],
            TYPE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_value)],
            SELECT_PAYMENT_METHOD: [CallbackQueryHandler(select_payment_method)],
            TYPE_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_location)],
            SELECT_PURCHASE_TYPE: [CallbackQueryHandler(select_purchase_type)],
            TYPE_TOTAL_INSTALLMENTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, type_total_installments)
            ],
            TYPE_CURRENT_INSTALLMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, type_current_installment)
            ],
            SELECT_DATE_OPTION: [CallbackQueryHandler(select_date_option)],
            TYPE_CUSTOM_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_custom_date)],
            CONFIRMATION: [CallbackQueryHandler(confirm_expense)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
