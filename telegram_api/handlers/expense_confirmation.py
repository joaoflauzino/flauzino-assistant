"""Date selection and confirmation steps for the expense conversation."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes, ConversationHandler

from telegram_api.handlers.expense_states import (
    CONFIRMATION,
    SELECT_DATE_OPTION,
    TYPE_CUSTOM_DATE,
)


async def ask_for_date(
    message_target: Message | CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    keyboard = [
        [
            InlineKeyboardButton("📅 Hoje (Agora)", callback_data="date_hoje"),
            InlineKeyboardButton("📅 Ontem", callback_data="date_ontem"),
        ],
        [
            InlineKeyboardButton("⌨️ Outra Data (Digitar)", callback_data="date_custom"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Qual foi a data da compra?"

    if isinstance(message_target, CallbackQuery):
        await message_target.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await message_target.reply_text(text=text, reply_markup=reply_markup)

    return SELECT_DATE_OPTION


async def select_date_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query is None or context.user_data is None:
        return SELECT_DATE_OPTION

    await query.answer()

    option = query.data or ""
    tz = ZoneInfo("America/Sao_Paulo")
    if option == "date_hoje":
        context.user_data["expense"]["created_at"] = datetime.now(tz)
        return await show_confirmation(query, context)
    elif option == "date_ontem":
        context.user_data["expense"]["created_at"] = datetime.now(tz) - timedelta(days=1)
        return await show_confirmation(query, context)
    elif option == "date_custom":
        await query.edit_message_text(
            "Por favor, digite a data no formato DD/MM/AAAA (ex: 15/06/2026):"
        )
        return TYPE_CUSTOM_DATE
    return SELECT_DATE_OPTION


async def type_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    if message is None or message.text is None or context.user_data is None:
        return TYPE_CUSTOM_DATE

    text = message.text
    try:
        dt = datetime.strptime(text, "%d/%m/%Y")
        tz = ZoneInfo("America/Sao_Paulo")
        now = datetime.now(tz)
        dt = dt.replace(hour=now.hour, minute=now.minute, second=now.second, tzinfo=tz)
        context.user_data["expense"]["created_at"] = dt
    except ValueError:
        await message.reply_text(
            "Formato inválido. Por favor, digite no formato DD/MM/AAAA (ex: 15/06/2026):"
        )
        return TYPE_CUSTOM_DATE

    return await show_confirmation(message, context)


async def show_confirmation(
    message_target: Message | CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    if context.user_data is None:
        return ConversationHandler.END

    expense = context.user_data["expense"]

    ptype = expense.get("purchase_type", "a_vista")
    ptype_str = "À vista"
    if ptype == "parcelada":
        ptype_str = f"Parcelada ({expense.get('current_installment', 1)}/{expense.get('total_installments', 1)})"
    elif ptype == "assinatura":
        ptype_str = "Assinatura Contínua"

    created_at_dt = expense.get("created_at")
    date_str = created_at_dt.strftime("%d/%m/%Y") if created_at_dt else "Hoje (Agora)"

    summary = (
        "Confira os dados do seu gasto:\n"
        f"- Categoria: {expense.get('category')}\n"
        f"- Item: {expense.get('item_bought')}\n"
        f"- Valor: R$ {expense.get('amount'):.2f}\n"
        f"- Pagamento: {expense.get('payment_method')}\n"
        f"- Local: {expense.get('location', 'N/A')}\n"
        f"- Data: {date_str}\n"
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

    if isinstance(message_target, CallbackQuery):
        await message_target.edit_message_text(text=summary, reply_markup=reply_markup)
    else:
        await message_target.reply_text(summary, reply_markup=reply_markup)

    return CONFIRMATION
