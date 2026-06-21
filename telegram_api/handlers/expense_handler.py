from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from telegram_api.core.logger import get_logger
from telegram_api.core.http_client import (
    get_valid_categories,
    get_valid_payment_methods,
    get_valid_owners,
    save_spent,
    save_subscription,
)

logger = get_logger(__name__)

(
    SELECT_CATEGORY,
    TYPE_ITEM_BOUGHT,
    TYPE_VALUE,
    SELECT_PAYMENT_METHOD,
    SELECT_OWNER,
    TYPE_LOCATION,
    SELECT_PURCHASE_TYPE,
    TYPE_TOTAL_INSTALLMENTS,
    TYPE_CURRENT_INSTALLMENT,
    CONFIRMATION,
) = range(10)


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
    await query.answer()

    context.user_data["expense"]["category"] = query.data
    logger.info(f"Selected category: {query.data}")

    await query.edit_message_text(
        text=f"Categoria selecionada: {query.data}\n\nO que você comprou?"
    )
    return TYPE_ITEM_BOUGHT


async def type_item_bought(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    context.user_data["expense"]["item_bought"] = text
    logger.info(f"Typed item bought: {text}")

    await update.message.reply_text("Qual foi o valor?")
    return TYPE_VALUE


async def type_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    try:
        value = float(text.replace(",", "."))
        context.user_data["expense"]["amount"] = value
    except ValueError:
        await update.message.reply_text(
            "Valor inválido. Por favor, digite um número (ex: 50.00 ou 50,00)."
        )
        return TYPE_VALUE

    logger.info(f"Typed value: {value}")

    payment_methods = await get_valid_payment_methods()
    reply_markup = build_inline_keyboard(payment_methods)

    await update.message.reply_text(
        "Qual foi o método de pagamento?",
        reply_markup=reply_markup,
    )
    return SELECT_PAYMENT_METHOD


async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    context.user_data["expense"]["payment_method"] = query.data
    logger.info(f"Selected payment method: {query.data}")

    owners = await get_valid_owners()
    reply_markup = build_inline_keyboard(owners)

    await query.edit_message_text(
        text=f"Método de pagamento: {query.data}\n\nDe quem é o cartão/conta?",
        reply_markup=reply_markup,
    )
    return SELECT_OWNER


async def select_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    context.user_data["expense"]["payment_owner"] = query.data
    logger.info(f"Selected owner: {query.data}")

    await query.edit_message_text(text=f"Proprietário: {query.data}\n\nOnde foi a compra? (Local)")
    return TYPE_LOCATION


async def type_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
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

    await update.message.reply_text("Qual o tipo dessa despesa?", reply_markup=reply_markup)
    return SELECT_PURCHASE_TYPE


async def show_confirmation(message_target, context: ContextTypes.DEFAULT_TYPE) -> int:
    expense = context.user_data["expense"]

    ptype = expense.get("purchase_type", "a_vista")
    ptype_str = "À vista"
    if ptype == "parcelada":
        ptype_str = f"Parcelada ({expense.get('current_installment', 1)}/{expense.get('total_installments', 1)})"
    elif ptype == "assinatura":
        ptype_str = "Assinatura Contínua"

    summary = (
        "Confira os dados do seu gasto:\n"
        f"- Categoria: {expense.get('category')}\n"
        f"- Item: {expense.get('item_bought')}\n"
        f"- Valor: R$ {expense.get('amount'):.2f}\n"
        f"- Pagamento: {expense.get('payment_method')}\n"
        f"- Proprietário: {expense.get('payment_owner')}\n"
        f"- Local: {expense.get('location', 'N/A')}\n"
        f"- Tipo: {ptype_str}\n\n"
        "Tudo correto?"
    )

    keyboard = [
        [
            InlineKeyboardButton("Sim, confirmar", callback_data="confirm"),
            InlineKeyboardButton("Não, cancelar", callback_data="cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(message_target, "edit_message_text"):
        await message_target.edit_message_text(text=summary, reply_markup=reply_markup)
    else:
        await message_target.reply_text(summary, reply_markup=reply_markup)

    return CONFIRMATION


async def select_purchase_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    purchase_type = query.data
    context.user_data["expense"]["purchase_type"] = purchase_type
    logger.info(f"Selected purchase type: {purchase_type}")

    if purchase_type == "parcelada":
        await query.edit_message_text(text="Em quantas vezes foi dividido? (Ex: 10)")
        return TYPE_TOTAL_INSTALLMENTS

    return await show_confirmation(query, context)


async def type_total_installments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    try:
        total = int(text)
        if total < 2:
            raise ValueError()
        context.user_data["expense"]["total_installments"] = total
    except ValueError:
        await update.message.reply_text("Por favor, digite um número inteiro maior que 1.")
        return TYPE_TOTAL_INSTALLMENTS

    await update.message.reply_text(
        "Essa é a parcela de número X? (Ex: 1 se for nova, 5 se for uma compra em andamento)"
    )
    return TYPE_CURRENT_INSTALLMENT


async def type_current_installment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    total = context.user_data["expense"]["total_installments"]
    try:
        current = int(text)
        if current < 1 or current > total:
            raise ValueError()
        context.user_data["expense"]["current_installment"] = current
    except ValueError:
        await update.message.reply_text(f"Por favor, digite um número entre 1 e {total}.")
        return TYPE_CURRENT_INSTALLMENT

    return await show_confirmation(update.message, context)


async def confirm_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "confirm":
        expense = context.user_data.get("expense", {})
        try:
            ptype = expense.get("purchase_type", "a_vista")

            if ptype == "assinatura":
                sub_data = {
                    "name": expense.get("item_bought"),
                    "category": expense.get("category"),
                    "amount": expense.get("amount"),
                    "payment_method": expense.get("payment_method"),
                    "payment_owner": expense.get("payment_owner"),
                }
                await save_subscription(sub_data)
            else:
                spent_data = {
                    "category": expense.get("category"),
                    "amount": expense.get("amount"),
                    "item_bought": expense.get("item_bought"),
                    "payment_method": expense.get("payment_method"),
                    "payment_owner": expense.get("payment_owner"),
                    "location": expense.get("location", "N/A"),
                }
                if ptype == "parcelada":
                    spent_data["is_installment"] = True
                    spent_data["current_installment"] = expense.get("current_installment", 1)
                    spent_data["total_installments"] = expense.get("total_installments", 1)

                await save_spent(spent_data)

            await query.edit_message_text(text="✅ Registro salvo com sucesso!")
            logger.info("Saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save: {e}")
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
    await update.message.reply_text("Registro cancelado.")
    context.user_data.pop("expense", None)
    return ConversationHandler.END


expense_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("gasto", gasto_command)],
    states={
        SELECT_CATEGORY: [CallbackQueryHandler(select_category)],
        TYPE_ITEM_BOUGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_item_bought)],
        TYPE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_value)],
        SELECT_PAYMENT_METHOD: [CallbackQueryHandler(select_payment_method)],
        SELECT_OWNER: [CallbackQueryHandler(select_owner)],
        TYPE_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_location)],
        SELECT_PURCHASE_TYPE: [CallbackQueryHandler(select_purchase_type)],
        TYPE_TOTAL_INSTALLMENTS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, type_total_installments)
        ],
        TYPE_CURRENT_INSTALLMENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, type_current_installment)
        ],
        CONFIRMATION: [CallbackQueryHandler(confirm_expense)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
