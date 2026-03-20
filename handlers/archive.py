from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config import get_settings
from db import db
from utils.keyboards import main_menu_kb
from utils.models import OrderStatus
from utils.services import ARCHIVE_STATUSES

from .common import deadline_to_user_string, get_user_by_tg

settings = get_settings()
router = Router()


@router.callback_query(F.data == "menu:archive")
async def show_archive(callback: CallbackQuery):
    user = await get_user_by_tg(callback.from_user.id)
    assert db.pool is not None
    orders = await db.pool.fetch(
        """
        SELECT title, deadline, status FROM orders
        WHERE user_id = $1 AND status = ANY($2::text[]) AND updated_at >= NOW() - INTERVAL '90 days'
        ORDER BY updated_at DESC
        LIMIT $3
        """,
        user["id"],
        ARCHIVE_STATUSES,
        int(user["page_size"]),
    )
    if not orders:
        await callback.message.edit_text("Архив пуст.", reply_markup=main_menu_kb(callback.from_user.id in settings.admin_ids))
    else:
        text = "Архив заказов:\n\n" + "\n".join(
            [f"{'✅' if o['status'] == OrderStatus.COMPLETED.value else '⛔'} {o['title']} — {deadline_to_user_string(o['deadline'], user['timezone'])}" for o in orders]
        )
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Главное меню", callback_data="menu:main")]]))
    await callback.answer()
