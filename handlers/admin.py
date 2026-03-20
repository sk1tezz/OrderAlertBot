from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from config import get_settings
from db import db
from utils.keyboards import main_menu_kb
from utils.models import OrderStatus
from utils.services import ACTIVE_STATUSES

settings = get_settings()
router = Router()


@router.callback_query(F.data == "menu:stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("Нет доступа", show_alert=True)
        return
    assert db.pool is not None
    users_count = await db.pool.fetchval("SELECT COUNT(*) FROM users")
    active_count = await db.pool.fetchval("SELECT COUNT(*) FROM orders WHERE status = ANY($1::text[])", ACTIVE_STATUSES)
    month_completed = await db.pool.fetchval(
        "SELECT COUNT(*) FROM orders WHERE status = $1 AND updated_at >= NOW() - INTERVAL '30 days'",
        OrderStatus.COMPLETED.value,
    )
    overdue_count = await db.pool.fetchval("SELECT COUNT(*) FROM orders WHERE status = $1", OrderStatus.OVERDUE.value)
    await callback.message.edit_text(
        "Статистика бота:\n\n"
        f"Пользователей:           {users_count}\n"
        f"Активных заказов:        {active_count}\n"
        f"Завершённых за месяц:    {month_completed}\n"
        f"Просроченных сейчас:     {overdue_count}",
        reply_markup=main_menu_kb(True),
    )
    await callback.answer()
