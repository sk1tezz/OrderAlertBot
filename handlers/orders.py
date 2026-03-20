from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config import get_settings
from db import db
from utils.keyboards import main_menu_kb
from utils.models import OrderStatus
from utils.services import ACTIVE_STATUSES, format_left, now_utc, status_marker

from .common import deadline_to_user_string, get_user_by_tg

settings = get_settings()
router = Router()

STATUS_RU = {
    OrderStatus.ACTIVE.value: "Активный",
    OrderStatus.UPCOMING.value: "Скоро",
    OrderStatus.OVERDUE.value: "Просрочен",
    OrderStatus.COMPLETED.value: "Завершён",
    OrderStatus.CANCELLED.value: "Отменён",
}


async def _render_orders(callback: CallbackQuery, page: int):
    user = await get_user_by_tg(callback.from_user.id)
    assert db.pool is not None
    orders = await db.pool.fetch(
        """
        SELECT id, title, deadline, status
        FROM orders
        WHERE user_id = $1 AND status = ANY($2::text[])
        ORDER BY deadline ASC;
        """,
        user["id"],
        ACTIVE_STATUSES,
    )
    if not orders:
        await callback.message.edit_text("У вас пока нет активных заказов.", reply_markup=main_menu_kb(callback.from_user.id in settings.admin_ids))
        return
    page_size = int(user["page_size"])
    start = (page - 1) * page_size
    chunk = orders[start : start + page_size]
    rows = [
        [InlineKeyboardButton(text=f"{status_marker(o['deadline'])} {o['title']} — {deadline_to_user_string(o['deadline'], user['timezone'])}", callback_data=f"order:view:{o['id']}")]
        for o in chunk
    ]
    max_page = (len(orders) + page_size - 1) // page_size
    rows.append(
        [
            InlineKeyboardButton(text="Назад", callback_data=f"menu:orders:{max(1, page - 1)}"),
            InlineKeyboardButton(text=f"Стр. {page}/{max_page}", callback_data="noop"),
            InlineKeyboardButton(text="Вперёд", callback_data=f"menu:orders:{min(max_page, page + 1)}"),
        ]
    )
    rows.append([InlineKeyboardButton(text="Главное меню", callback_data="menu:main")])
    await callback.message.edit_text("Ваши активные заказы:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("menu:orders"))
async def orders_list(callback: CallbackQuery):
    page = int(callback.data.split(":")[-1]) if callback.data.count(":") == 2 else 1
    await _render_orders(callback, page)
    await callback.answer()


@router.callback_query(F.data.startswith("order:view:"))
async def order_view(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[-1])
    user = await get_user_by_tg(callback.from_user.id)
    assert db.pool is not None
    order = await db.pool.fetchrow("SELECT * FROM orders WHERE id = $1 AND user_id = $2", order_id, user["id"])
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    left = format_left(order["deadline"] - now_utc()) if order["status"] in ACTIVE_STATUSES else "—"
    status_text = STATUS_RU.get(order["status"], order["status"])
    text = (
        f"Заказ N{order['id']}\n\nНазвание: {order['title']}\nОписание: {order['description'] or '—'}\n"
        f"Дедлайн: {deadline_to_user_string(order['deadline'], user['timezone'])}\nОсталось: {left}\n"
        f"Статус: {status_text}\nСоздан: {deadline_to_user_string(order['created_at'], user['timezone'])}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Завершить", callback_data=f"order:complete:{order_id}"), InlineKeyboardButton(text="Удалить", callback_data=f"order:delete:{order_id}")],
            [InlineKeyboardButton(text="К списку", callback_data="menu:orders:1")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("order:complete:"))
async def order_complete(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[-1])
    user = await get_user_by_tg(callback.from_user.id)
    assert db.pool is not None
    await db.pool.execute(
        "UPDATE orders SET status = $1, updated_at = NOW() WHERE id = $2 AND user_id = $3",
        OrderStatus.COMPLETED.value,
        order_id,
        user["id"],
    )
    await db.pool.execute("DELETE FROM reminders_log WHERE order_id = $1", order_id)
    await callback.answer("Заказ завершён", show_alert=True)
    await _render_orders(callback, 1)


@router.callback_query(F.data.startswith("order:delete:"))
async def order_delete(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[-1])
    user = await get_user_by_tg(callback.from_user.id)
    assert db.pool is not None
    await db.pool.execute("DELETE FROM orders WHERE id = $1 AND user_id = $2", order_id, user["id"])
    await callback.answer("Заказ удалён", show_alert=True)
    await _render_orders(callback, 1)
