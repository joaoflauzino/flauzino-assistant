from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)
import httpx
import base64

from telegram_api.core.logger import get_logger
from telegram_api.core.http_client import get_valid_categories
from telegram_api.settings import settings

logger = get_logger(__name__)

SELECT_CATEGORY = range(1)


def build_inline_keyboard(
    categories: list[str], selected: set[str], columns: int = 2
) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for cat in categories:
        text = f"✅ {cat}" if cat in selected else cat
        row.append(InlineKeyboardButton(text, callback_data=f"cat:{cat}"))
        if len(row) == columns:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Actions row
    action_row = [
        InlineKeyboardButton("✅ Todas", callback_data="all"),
        InlineKeyboardButton("Nenhuma", callback_data="none"),
    ]
    keyboard.append(action_row)

    keyboard.append([InlineKeyboardButton("📊 Gerar Gráfico", callback_data="generate")])
    return InlineKeyboardMarkup(keyboard)


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the balance consultation flow and return a graph."""
    logger.info(f"User {update.effective_user.id} requested balance graph via command")

    command_used = update.message.text.split()[0].replace("/", "").lower()
    context.user_data["balance_mode"] = command_used
    context.user_data["selected_categories"] = set()

    categories = await get_valid_categories()
    context.user_data["available_categories"] = categories

    reply_markup = build_inline_keyboard(categories, context.user_data["selected_categories"])

    await update.message.reply_text(
        "Selecione as categorias que deseja visualizar:",
        reply_markup=reply_markup,
    )
    return SELECT_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data
    selected = context.user_data.get("selected_categories", set())
    categories = context.user_data.get("available_categories", [])
    mode = context.user_data.get("balance_mode", "saldo")

    if data == "all":
        selected = set(categories)
        context.user_data["selected_categories"] = selected
        await query.edit_message_reply_markup(
            reply_markup=build_inline_keyboard(categories, selected)
        )
        return SELECT_CATEGORY

    elif data == "none":
        selected = set()
        context.user_data["selected_categories"] = selected
        await query.edit_message_reply_markup(
            reply_markup=build_inline_keyboard(categories, selected)
        )
        return SELECT_CATEGORY

    elif data.startswith("cat:"):
        cat = data.split("cat:")[1]
        if cat in selected:
            selected.remove(cat)
        else:
            selected.add(cat)
        context.user_data["selected_categories"] = selected
        await query.edit_message_reply_markup(
            reply_markup=build_inline_keyboard(categories, selected)
        )
        return SELECT_CATEGORY

    elif data == "generate":
        if not selected:
            selected = set(categories)  # Default to all if none selected

        await query.edit_message_text("Gerando gráfico dos seus saldos, aguarde...")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                finance_url = f"{settings.FINANCE_SERVICE_URL}/limits/balance"
                fin_resp = await client.get(finance_url)
                if fin_resp.status_code == 404:
                    await query.edit_message_text(
                        "Você ainda não possui limites de gastos cadastrados para este mês."
                    )
                    return ConversationHandler.END
                fin_resp.raise_for_status()
                balances = fin_resp.json()

                if not balances:
                    await query.edit_message_text(
                        "Você ainda não possui limites de gastos cadastrados para este mês."
                    )
                    return ConversationHandler.END

                selected_lower = {s.lower().strip() for s in selected}
                filtered_balances = [
                    b
                    for b in balances
                    if b.get("category", "").lower() in selected_lower
                    or b.get("category_display_name", "").lower() in selected_lower
                ] or balances

                graph_url = f"{settings.GRAPH_SERVICE_URL}/graphs/bar"
                response = await client.post(
                    graph_url,
                    json={
                        "balances": filtered_balances,
                        "mode": mode,
                    },
                )
                response.raise_for_status()
                data = response.json()

                if "image_base64" in data:
                    img_data = base64.b64decode(data["image_base64"])
                    await update.effective_message.reply_photo(
                        photo=img_data, caption=f"Aqui está o gráfico de {mode}."
                    )
                    await query.message.delete()
                else:
                    await query.edit_message_text(
                        "Desculpe, o formato do gráfico recebido é inválido."
                    )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching balance graph: {e}")
            await query.edit_message_text("Desculpe, não consegui gerar o gráfico no momento.")
        except Exception as e:
            logger.error(f"Unexpected error fetching balance graph: {e}")
            await query.edit_message_text("Ocorreu um erro inesperado ao gerar o gráfico.")

        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Consulta cancelada.")
    return ConversationHandler.END


balance_handlers = [
    ConversationHandler(
        entry_points=[
            CommandHandler("saldo", balance_command),
            CommandHandler("limites", balance_command),
        ],
        states={
            SELECT_CATEGORY: [CallbackQueryHandler(select_category)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
]
