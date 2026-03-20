from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from db import db
from utils.keyboards import (
    calendar_deadline_kb,
    cancel_kb,
    create_confirm_kb,
    create_edit_fields_kb,
    post_create_kb,
    skip_cancel_kb,
    time_deadline_kb,
)
from utils.models import OrderStatus
from utils.services import ACTIVE_STATUSES, now_utc
from utils.states import CreateOrderState

from .common import get_user_by_tg, render_confirm

router = Router()


def _parse_time_hh_mm(t: str) -> time:
    t = t.replace("_", ":")
    hh, mm = t.split(":")
    return time(hour=int(hh), minute=int(mm))


def _local_today(tz_name: str) -> date:
    return datetime.now(ZoneInfo(tz_name)).date()


@router.callback_query(F.data == "menu:new_order")
async def new_order_start(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_tg(callback.from_user.id)
    if not user:
        await callback.answer("Сначала отправьте /start", show_alert=True)
        return
    assert db.pool is not None
    active_count = await db.pool.fetchval(
        "SELECT COUNT(*) FROM orders WHERE user_id = $1 AND status = ANY($2::text[])",
        user["id"],
        ACTIVE_STATUSES,
    )
    if int(active_count) >= 50:
        await callback.answer("Достигнут лимит 50 активных заказов", show_alert=True)
        return
    await state.clear()
    await state.set_state(CreateOrderState.title)
    await callback.message.edit_text("Введите название заказа:", reply_markup=cancel_kb())
    await callback.answer()


@router.message(CreateOrderState.title)
async def create_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым.")
        return
    if len(title) > 255:
        await message.answer("Название длиннее 255 символов.")
        return
    await state.update_data(title=title)
    await state.set_state(CreateOrderState.description)
    await message.answer("Введите описание заказа или нажмите Пропустить:", reply_markup=skip_cancel_kb())


@router.callback_query(CreateOrderState.description, F.data == "create:skip_description")
async def create_skip_description(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description=None)
    user = await get_user_by_tg(callback.from_user.id)
    assert user is not None
    today = _local_today(user["timezone"])
    await state.set_state(CreateOrderState.deadline_date)
    await state.update_data(deadline_date=None, deadline_time=None)
    await callback.message.edit_text(
        "Выберите дату дедлайна (время выберете на следующем шаге):",
        reply_markup=calendar_deadline_kb(
            year=today.year,
            month=today.month,
            timezone_name=user["timezone"],
            selected_date=None,
            min_date=today,
            include_quick=True,
        ),
    )
    await callback.answer()


@router.message(CreateOrderState.description)
async def create_description(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if len(text) > 2000:
        await message.answer("Описание длиннее 2000 символов.")
        return
    await state.update_data(description=text)
    user = await get_user_by_tg(message.from_user.id)
    assert user is not None
    today = _local_today(user["timezone"])
    await state.set_state(CreateOrderState.deadline_date)
    await state.update_data(deadline_date=None, deadline_time=None)
    await message.answer(
        "Выберите дату дедлайна (время выберете на следующем шаге):",
        reply_markup=calendar_deadline_kb(
            year=today.year,
            month=today.month,
            timezone_name=user["timezone"],
            selected_date=None,
            min_date=today,
            include_quick=True,
        ),
    )


@router.callback_query(CreateOrderState.deadline_date, F.data == "create:deadline:tomorrow")
async def deadline_quick_tomorrow(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_tg(callback.from_user.id)
    assert user is not None
    target_date = _local_today(user["timezone"]) + timedelta(days=1)
    await state.update_data(deadline_date=target_date.isoformat(), deadline_time=None)
    await state.set_state(CreateOrderState.deadline_time)
    await callback.message.edit_text("Выберите время:", reply_markup=time_deadline_kb())
    await callback.answer()


@router.callback_query(CreateOrderState.deadline_date, F.data == "create:deadline:3days")
async def deadline_quick_3days(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_tg(callback.from_user.id)
    assert user is not None
    target_date = _local_today(user["timezone"]) + timedelta(days=3)
    await state.update_data(deadline_date=target_date.isoformat(), deadline_time=None)
    await state.set_state(CreateOrderState.deadline_time)
    await callback.message.edit_text("Выберите время:", reply_markup=time_deadline_kb())
    await callback.answer()


@router.callback_query(CreateOrderState.deadline_date, F.data == "create:deadline:7days")
async def deadline_quick_7days(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_tg(callback.from_user.id)
    assert user is not None
    target_date = _local_today(user["timezone"]) + timedelta(days=7)
    await state.update_data(deadline_date=target_date.isoformat(), deadline_time=None)
    await state.set_state(CreateOrderState.deadline_time)
    await callback.message.edit_text("Выберите время:", reply_markup=time_deadline_kb())
    await callback.answer()


@router.callback_query(CreateOrderState.deadline_date, F.data.startswith("create:deadline:cal:"))
async def deadline_calendar_nav(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_tg(callback.from_user.id)
    assert user is not None
    _, _, _, year_s, month_s = callback.data.split(":")
    year = int(year_s)
    month = int(month_s)

    data = await state.get_data()
    selected_date = date.fromisoformat(data["deadline_date"]) if data.get("deadline_date") else None
    today = _local_today(user["timezone"])

    await callback.message.edit_text(
        "Выберите дату дедлайна (время выберете на следующем шаге):",
        reply_markup=calendar_deadline_kb(
            year=year,
            month=month,
            timezone_name=user["timezone"],
            selected_date=selected_date,
            min_date=today,
            include_quick=True,
        ),
    )
    await callback.answer()


@router.callback_query(CreateOrderState.deadline_date, F.data.startswith("create:deadline:date:"))
async def deadline_pick_date(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_tg(callback.from_user.id)
    assert user is not None
    selected = callback.data.split(":")[-1]
    chosen_date = date.fromisoformat(selected)
    await state.update_data(deadline_date=chosen_date.isoformat(), deadline_time=None)
    await state.set_state(CreateOrderState.deadline_time)
    await callback.message.edit_text("Выберите время:", reply_markup=time_deadline_kb())
    await callback.answer()


@router.callback_query(CreateOrderState.deadline_time, F.data == "create:deadline:back_to_date")
async def deadline_back_to_date(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_tg(callback.from_user.id)
    assert user is not None

    data = await state.get_data()
    selected_date = date.fromisoformat(data["deadline_date"]) if data.get("deadline_date") else _local_today(user["timezone"])
    today = _local_today(user["timezone"])

    await state.set_state(CreateOrderState.deadline_date)
    await callback.message.edit_text(
        "Выберите дату дедлайна (время выберете на следующем шаге):",
        reply_markup=calendar_deadline_kb(
            year=selected_date.year,
            month=selected_date.month,
            timezone_name=user["timezone"],
            selected_date=selected_date,
            min_date=today,
            include_quick=True,
        ),
    )
    await callback.answer()


@router.callback_query(CreateOrderState.deadline_time, F.data.startswith("create:deadline:time:"))
async def deadline_pick_time(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_tg(callback.from_user.id)
    assert user is not None

    data = await state.get_data()
    deadline_date_s = data.get("deadline_date")
    if not deadline_date_s:
        await callback.answer("Сначала выберите дату.", show_alert=True)
        return
    chosen_date = date.fromisoformat(deadline_date_s)

    raw_time = callback.data.split(":")[-1]
    chosen_time = _parse_time_hh_mm(raw_time)

    local_dt = datetime(
        year=chosen_date.year,
        month=chosen_date.month,
        day=chosen_date.day,
        hour=chosen_time.hour,
        minute=chosen_time.minute,
        tzinfo=ZoneInfo(user["timezone"]),
    )
    deadline_utc = local_dt.astimezone(ZoneInfo("UTC"))

    if deadline_utc <= now_utc():
        await callback.answer("Выберите время в будущем.", show_alert=True)
        return

    await state.update_data(deadline=deadline_utc, deadline_time=raw_time.replace("_", ":"))
    await state.set_state(CreateOrderState.confirm)
    data = await state.get_data()
    await callback.message.edit_text(render_confirm(data, user["timezone"]), reply_markup=create_confirm_kb())
    await callback.answer()


@router.callback_query(CreateOrderState.confirm, F.data == "create:confirm:edit")
async def create_confirm_edit(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateOrderState.edit_pick_field)
    await callback.message.edit_text("Что хотите изменить?", reply_markup=create_edit_fields_kb())
    await callback.answer()


@router.callback_query(CreateOrderState.edit_pick_field, F.data == "create:back_to_confirm")
async def create_back_to_confirm(callback: CallbackQuery, state: FSMContext):
    user = await get_user_by_tg(callback.from_user.id)
    data = await state.get_data()
    await state.set_state(CreateOrderState.confirm)
    await callback.message.edit_text(render_confirm(data, user["timezone"]), reply_markup=create_confirm_kb())
    await callback.answer()


@router.callback_query(CreateOrderState.edit_pick_field, F.data.startswith("create:edit:"))
async def create_pick_edit_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[-1]
    await state.update_data(edit_field=field)

    if field == "deadline":
        user = await get_user_by_tg(callback.from_user.id)
        assert user is not None
        data = await state.get_data()
        selected_utc = data.get("deadline")
        selected_date = (
            selected_utc.astimezone(ZoneInfo(user["timezone"])).date() if selected_utc else _local_today(user["timezone"])
        )
        today = _local_today(user["timezone"])

        await state.update_data(deadline_date=selected_date.isoformat(), deadline_time=None)
        await state.set_state(CreateOrderState.deadline_date)
        await callback.message.edit_text(
            "Выберите новую дату дедлайна (время выберете на следующем шаге):",
            reply_markup=calendar_deadline_kb(
                year=selected_date.year,
                month=selected_date.month,
                timezone_name=user["timezone"],
                selected_date=selected_date,
                min_date=today,
                include_quick=True,
            ),
        )
        await callback.answer()
        return

    await state.set_state(CreateOrderState.edit_value)
    prompts = {"title": "Введите новое название:", "description": "Введите новое описание (или '-'): "}
    await callback.message.edit_text(prompts[field], reply_markup=cancel_kb())
    await callback.answer()


@router.message(CreateOrderState.edit_value)
async def create_set_edited_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("edit_field")
    value = (message.text or "").strip()
    if field == "title":
        if len(value) == 0 or len(value) > 255:
            await message.answer("Название должно быть 1..255 символов.")
            return
        await state.update_data(title=value)
    elif field == "description":
        if value == "-":
            value = None
        if value and len(value) > 2000:
            await message.answer("Описание не должно превышать 2000 символов.")
            return
        await state.update_data(description=value)
    user = await get_user_by_tg(message.from_user.id)
    data = await state.get_data()
    await state.set_state(CreateOrderState.confirm)
    await message.answer(render_confirm(data, user["timezone"]), reply_markup=create_confirm_kb())


@router.callback_query(CreateOrderState.confirm, F.data == "create:confirm:save")
async def create_confirm_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await get_user_by_tg(callback.from_user.id)
    assert db.pool is not None
    row = await db.pool.fetchrow(
        """
        INSERT INTO orders (user_id, title, description, deadline, status)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id;
        """,
        user["id"],
        data["title"],
        data.get("description"),
        data["deadline"],
        OrderStatus.ACTIVE.value,
    )
    await state.clear()
    await callback.message.edit_text(f"Заказ N{row['id']} создан! Я напомню вам заранее.", reply_markup=post_create_kb())
    await callback.answer()
