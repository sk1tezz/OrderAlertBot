from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from db import db
from utils.keyboards import settings_kb, timezone_kb

from .common import get_user_by_tg

router = Router()


async def _refresh_settings_message(callback: CallbackQuery) -> None:
    user = await get_user_by_tg(callback.from_user.id)
    text = (
        "Настройки\n\n"
        f"Часовой пояс:         {user['timezone']}\n"
        f"Напоминания:          {'Включены' if any([user['notify_24h'], user['notify_3h'], user['notify_1h']]) else 'Выключены'}\n"
        f"  За 24 часа:         {'Да' if user['notify_24h'] else 'Нет'}\n"
        f"  За 3 часа:          {'Да' if user['notify_3h'] else 'Нет'}\n"
        f"  За 1 час:           {'Да' if user['notify_1h'] else 'Нет'}\n"
        f"Заказов на странице:  {user['page_size']}"
    )
    await callback.message.edit_text(text, reply_markup=settings_kb(user))


@router.callback_query(F.data == "menu:settings")
async def menu_settings(callback: CallbackQuery):
    await _refresh_settings_message(callback)
    await callback.answer()


@router.callback_query(F.data.startswith("settings:toggle:"))
async def toggle_notify(callback: CallbackQuery):
    key = callback.data.split(":")[-1]
    field = {"24h": "notify_24h", "3h": "notify_3h", "1h": "notify_1h"}[key]
    user = await get_user_by_tg(callback.from_user.id)
    assert db.pool is not None
    await db.pool.execute(f"UPDATE users SET {field} = $1, updated_at = NOW() WHERE id = $2", not user[field], user["id"])
    await _refresh_settings_message(callback)
    await callback.answer()


@router.callback_query(F.data == "settings:timezone")
async def settings_timezone(callback: CallbackQuery):
    await callback.message.edit_text("Выберите часовой пояс:", reply_markup=timezone_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("settings:tz:"))
async def set_timezone(callback: CallbackQuery):
    zone = callback.data.split(":", 2)[-1]
    user = await get_user_by_tg(callback.from_user.id)
    assert db.pool is not None
    await db.pool.execute("UPDATE users SET timezone = $1, updated_at = NOW() WHERE id = $2", zone, user["id"])
    await callback.answer("Часовой пояс обновлён", show_alert=True)
    await _refresh_settings_message(callback)


@router.callback_query(F.data == "settings:page_size")
async def settings_page_size(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="3", callback_data="settings:page_set:3"), InlineKeyboardButton(text="5", callback_data="settings:page_set:5"), InlineKeyboardButton(text="10", callback_data="settings:page_set:10")],
            [InlineKeyboardButton(text="Назад к настройкам", callback_data="menu:settings")],
        ]
    )
    await callback.message.edit_text("Сколько заказов показывать на одной странице?", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("settings:page_set:"))
async def settings_page_size_set(callback: CallbackQuery):
    value = int(callback.data.split(":")[-1])
    user = await get_user_by_tg(callback.from_user.id)
    assert db.pool is not None
    await db.pool.execute("UPDATE users SET page_size = $1, updated_at = NOW() WHERE id = $2", value, user["id"])
    await _refresh_settings_message(callback)
    await callback.answer()
