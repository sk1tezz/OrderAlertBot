from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import get_settings
from utils.keyboards import main_menu_kb

from .common import get_or_create_user, get_user_by_tg, show_main_menu

settings = get_settings()
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(message.from_user)
    await show_main_menu(message, user)


@router.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_user_by_tg(callback.from_user.id)
    if user:
        await show_main_menu(callback, user)
    await callback.answer()


@router.callback_query(F.data == "common:cancel")
async def cancel_any(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await get_user_by_tg(callback.from_user.id)
    if user:
        await show_main_menu(callback, user)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.message()
async def fallback_text(message: Message, state: FSMContext):
    if await state.get_state():
        await message.answer("Пожалуйста, используйте кнопки или завершите текущий шаг.")
        return
    user = await get_user_by_tg(message.from_user.id)
    if user:
        await message.answer("Я работаю через кнопки. Вот главное меню:", reply_markup=main_menu_kb(user["telegram_id"] in settings.admin_ids))
