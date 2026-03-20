from __future__ import annotations

from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from config import get_settings
from db import db
from utils.keyboards import main_menu_kb
from utils.services import format_left, now_utc

settings = get_settings()


def deadline_to_user_string(deadline_utc, timezone_name: str) -> str:
    return deadline_utc.astimezone(ZoneInfo(timezone_name)).strftime("%d.%m.%Y %H:%M")


async def get_user_by_tg(telegram_id: int):
    assert db.pool is not None
    return await db.pool.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)


async def get_or_create_user(tg_user):
    user = await get_user_by_tg(tg_user.id)
    if user:
        return user
    assert db.pool is not None
    return await db.pool.fetchrow(
        """
        INSERT INTO users (telegram_id, username, first_name)
        VALUES ($1, $2, $3)
        RETURNING *;
        """,
        tg_user.id,
        tg_user.username,
        tg_user.first_name,
    )


async def show_main_menu(target: Message | CallbackQuery, user) -> None:
    text = (
        f"Добро пожаловать, {user['first_name'] or 'друг'}!\n\n"
        "Я помогу вам не забыть о важных заказах.\n"
        "Выберите действие:"
    )
    kb = main_menu_kb(user["telegram_id"] in settings.admin_ids)
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            await target.message.answer(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


def render_confirm(data: dict, timezone_name: str) -> str:
    local = data["deadline"].astimezone(ZoneInfo(timezone_name))
    return (
        "Проверьте данные заказа:\n\n"
        f"Название: {data['title']}\n"
        f"Описание: {data.get('description') or '—'}\n"
        f"Дедлайн: {local.strftime('%d.%m.%Y %H:%M')} (осталось {format_left(data['deadline'] - now_utc())})\n\n"
        "Всё верно?"
    )
