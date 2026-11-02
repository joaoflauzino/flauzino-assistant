from collections.abc import Awaitable, Callable, MutableMapping
from dataclasses import dataclass
from typing import Any

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from telegram_api.core.correlation import set_request_id
from telegram_api.core.finance_client import get_balance_graph, get_valid_categories
from telegram_api.core.logger import get_logger

logger = get_logger(__name__)

SELECT_CATEGORY = range(1)

CATEGORY_PREFIX = "cat:"


def build_inline_keyboard(
    categories: list[str], selected: set[str], columns: int = 2
) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for cat in categories:
        text = f"✅ {cat}" if cat in selected else cat
        row.append(InlineKeyboardButton(text, callback_data=f"{CATEGORY_PREFIX}{cat}"))
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


@dataclass(slots=True)
class CategorySelection:
    """Mutable view over the category selection stored in ``context.user_data``."""

    user_data: MutableMapping[str, Any]
    categories: list[str]

    @classmethod
    def load(cls, context: ContextTypes.DEFAULT_TYPE) -> "CategorySelection":
        user_data = context.user_data
        return cls(user_data=user_data, categories=list(user_data.get("available_categories", [])))

    @property
    def selected(self) -> set[str]:
        return self.user_data.get("selected_categories") or set()

    @property
    def mode(self) -> str:
        return self.user_data.get("balance_mode", "saldo")

    def select_all(self) -> None:
        self.user_data["selected_categories"] = set(self.categories)

    def select_none(self) -> None:
        self.user_data["selected_categories"] = set()

    def toggle(self, category: str) -> None:
        selected = self.selected
        if category in selected:
            selected.discard(category)
        else:
            selected.add(category)
        self.user_data["selected_categories"] = selected


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the balance consultation flow and return a graph."""
    set_request_id()
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


async def repaint(query: CallbackQuery, selection: CategorySelection) -> None:
    await query.edit_message_reply_markup(
        reply_markup=build_inline_keyboard(selection.categories, selection.selected)
    )


async def select_all(update: Update, selection: CategorySelection) -> int:
    selection.select_all()
    await repaint(update.callback_query, selection)
    return SELECT_CATEGORY


async def select_none(update: Update, selection: CategorySelection) -> int:
    selection.select_none()
    await repaint(update.callback_query, selection)
    return SELECT_CATEGORY


async def toggle_category(update: Update, selection: CategorySelection) -> int:
    data = update.callback_query.data or ""
    selection.toggle(data.removeprefix(CATEGORY_PREFIX))
    await repaint(update.callback_query, selection)
    return SELECT_CATEGORY


async def reply_with_graph(
    update: Update, query: CallbackQuery, categories: set[str], mode: str
) -> None:
    try:
        img_data = await get_balance_graph(categories=categories, mode=mode)
    except Exception as exc:  # Boundary: failures must not crash the conversation.
        logger.error(f"Error fetching balance graph: {exc}")
        await query.edit_message_text("Desculpe, não consegui gerar o gráfico no momento.")
        return

    if not img_data:
        await query.edit_message_text(
            "Você ainda não possui limites de gastos cadastrados para este mês."
        )
        return

    await update.effective_message.reply_photo(
        photo=img_data, caption=f"Aqui está o gráfico de {mode}."
    )
    await query.message.delete()


async def generate_graph(update: Update, selection: CategorySelection) -> int:
    query = update.callback_query
    selected = selection.selected or set(selection.categories)

    await query.edit_message_text("Gerando gráfico dos seus saldos, aguarde...")
    await reply_with_graph(update, query, selected, selection.mode)
    return ConversationHandler.END


async def ignore(update: Update, selection: CategorySelection) -> int:
    return SELECT_CATEGORY


CategoryAction = Callable[[Update, CategorySelection], Awaitable[int]]

ACTIONS: dict[str, CategoryAction] = {
    "all": select_all,
    "none": select_none,
    "generate": generate_graph,
}


def resolve_action(data: str) -> CategoryAction:
    if data.startswith(CATEGORY_PREFIX):
        return toggle_category
    return ACTIONS.get(data, ignore)


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    action = resolve_action(query.data or "")
    return await action(update, CategorySelection.load(context))


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
