from datetime import date, datetime, time
import calendar
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="+ Новый заказ", callback_data="menu:new_order")],
        [InlineKeyboardButton(text="Мои заказы", callback_data="menu:orders")],
        [InlineKeyboardButton(text="Архив", callback_data="menu:archive")],
        [InlineKeyboardButton(text="Настройки", callback_data="menu:settings")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="Статистика", callback_data="menu:stats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data="common:cancel")]]
    )


def skip_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="create:skip_description")],
            [InlineKeyboardButton(text="Отмена", callback_data="common:cancel")],
        ]
    )


def quick_deadline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Завтра", callback_data="create:deadline:tomorrow"),
                InlineKeyboardButton(text="Через 3 дня", callback_data="create:deadline:3days"),
            ],
            [
                InlineKeyboardButton(text="Через неделю", callback_data="create:deadline:7days"),
                InlineKeyboardButton(text="Отмена", callback_data="common:cancel"),
            ],
        ]
    )


def create_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сохранить", callback_data="create:confirm:save"),
                InlineKeyboardButton(text="Изменить", callback_data="create:confirm:edit"),
                InlineKeyboardButton(text="Отменить", callback_data="common:cancel"),
            ]
        ]
    )


def create_edit_fields_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Название", callback_data="create:edit:title"),
                InlineKeyboardButton(text="Описание", callback_data="create:edit:description"),
                InlineKeyboardButton(text="Дедлайн", callback_data="create:edit:deadline"),
            ],
            [InlineKeyboardButton(text="Назад к подтверждению", callback_data="create:back_to_confirm")],
        ]
    )


def post_create_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ещё один заказ", callback_data="menu:new_order"),
                InlineKeyboardButton(text="Мои заказы", callback_data="menu:orders"),
            ],
            [InlineKeyboardButton(text="Главное меню", callback_data="menu:main")],
        ]
    )


def settings_kb(user) -> InlineKeyboardMarkup:
    notify_24h = user["notify_24h"] if isinstance(user, dict) or hasattr(user, "__getitem__") else user.notify_24h
    notify_3h = user["notify_3h"] if isinstance(user, dict) or hasattr(user, "__getitem__") else user.notify_3h
    notify_1h = user["notify_1h"] if isinstance(user, dict) or hasattr(user, "__getitem__") else user.notify_1h
    page_size = user["page_size"] if isinstance(user, dict) or hasattr(user, "__getitem__") else user.page_size
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Часовой пояс", callback_data="settings:timezone")],
            [
                InlineKeyboardButton(
                    text=f"Напоминание за 24ч: {'Да' if notify_24h else 'Нет'}",
                    callback_data="settings:toggle:24h",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Напоминание за 3ч: {'Да' if notify_3h else 'Нет'}",
                    callback_data="settings:toggle:3h",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Напоминание за 1ч: {'Да' if notify_1h else 'Нет'}",
                    callback_data="settings:toggle:1h",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Заказов на странице: {page_size}",
                    callback_data="settings:page_size",
                )
            ],
            [InlineKeyboardButton(text="Главное меню", callback_data="menu:main")],
        ]
    )


def timezone_kb() -> InlineKeyboardMarkup:
    rows = [
        ("UTC+2 Калининград", "Europe/Kaliningrad"),
        ("UTC+3 Москва", "Europe/Moscow"),
        ("UTC+4 Самара", "Europe/Samara"),
        ("UTC+5 Екатеринбург", "Asia/Yekaterinburg"),
        ("UTC+6 Омск", "Asia/Omsk"),
        ("UTC+7 Красноярск", "Asia/Krasnoyarsk"),
        ("UTC+8 Иркутск", "Asia/Irkutsk"),
        ("UTC+9 Якутск", "Asia/Yakutsk"),
        ("UTC+10 Владивосток", "Asia/Vladivostok"),
        ("UTC+11 Магадан", "Asia/Magadan"),
        ("UTC+12 Камчатка", "Asia/Kamchatka"),
    ]
    keyboard_rows = [
        [
            InlineKeyboardButton(text=rows[i][0], callback_data=f"settings:tz:{rows[i][1]}"),
            InlineKeyboardButton(text=rows[i + 1][0], callback_data=f"settings:tz:{rows[i + 1][1]}"),
        ]
        for i in range(0, len(rows) - 1, 2)
    ]
    keyboard_rows.append([InlineKeyboardButton(text="Назад к настройкам", callback_data="menu:settings")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


_WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
_MONTHS_RU = [
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]


def time_deadline_kb(selected_time: str | None = None) -> InlineKeyboardMarkup:
    times = [f"{h:02d}:00" for h in range(0, 24)] + ["23:59"]
    cols = 5
    rows = []
    for i in range(0, len(times), cols):
        row = []
        for t in times[i : i + cols]:
            label = t
            if selected_time == t:
                label = f"✅ {t}"
            row.append(
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"create:deadline:time:{t.replace(':', '_')}",
                )
            )
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(text="Назад к дате", callback_data="create:deadline:back_to_date"),
            InlineKeyboardButton(text="Отмена", callback_data="common:cancel"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def calendar_deadline_kb(
    year: int,
    month: int,
    timezone_name: str,
    selected_date: date | None = None,
    min_date: date | None = None,
    include_quick: bool = True,
) -> InlineKeyboardMarkup:
    tz = ZoneInfo(timezone_name)
    today_local = datetime.now(tz).date()
    if min_date is None:
        min_date = today_local

    cal = calendar.Calendar(firstweekday=0)
    month_dates = list(cal.itermonthdates(year, month))

    rows: list[list[InlineKeyboardButton]] = []

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    month_title = f"{_MONTHS_RU[month - 1]} {year}"
    rows.append(
        [
            InlineKeyboardButton(text="<<", callback_data=f"create:deadline:cal:{prev_year}:{prev_month}"),
            InlineKeyboardButton(text=month_title, callback_data="noop"),
            InlineKeyboardButton(text=">>", callback_data=f"create:deadline:cal:{next_year}:{next_month}"),
        ]
    )
    rows.append([InlineKeyboardButton(text=d, callback_data="noop") for d in _WEEKDAYS_RU])

    for i in range(0, len(month_dates), 7):
        week = month_dates[i : i + 7]
        row: list[InlineKeyboardButton] = []
        for d in week:
            in_month = d.month == month
            is_past = d < min_date
            disabled = (not in_month) or is_past

            label = str(d.day)
            if selected_date and d == selected_date:
                label = f"✅ {d.day}"

            if disabled:
                row.append(InlineKeyboardButton(text=label, callback_data="noop"))
            else:
                row.append(
                    InlineKeyboardButton(
                        text=label,
                        callback_data=f"create:deadline:date:{d.isoformat()}",
                    )
                )
        rows.append(row)

    if include_quick:
        rows.append(
            [
                InlineKeyboardButton(text="Завтра", callback_data="create:deadline:tomorrow"),
                InlineKeyboardButton(text="Через 3 дня", callback_data="create:deadline:3days"),
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(text="Через неделю", callback_data="create:deadline:7days"),
                InlineKeyboardButton(text="Отмена", callback_data="common:cancel"),
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)
