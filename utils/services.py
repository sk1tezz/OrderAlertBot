from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .models import OrderStatus

ACTIVE_STATUSES = [OrderStatus.ACTIVE.value, OrderStatus.UPCOMING.value, OrderStatus.OVERDUE.value]
ARCHIVE_STATUSES = [OrderStatus.COMPLETED.value, OrderStatus.CANCELLED.value]


def now_utc() -> datetime:
    return datetime.now(tz=ZoneInfo("UTC"))


def format_left(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    if seconds <= 0:
        return "меньше минуты"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    chunks = []
    if days:
        chunks.append(f"{days} дн.")
    if hours:
        chunks.append(f"{hours} ч.")
    if minutes and len(chunks) < 2:
        chunks.append(f"{minutes} мин.")
    return " ".join(chunks) if chunks else "меньше минуты"


def status_marker(deadline_utc: datetime) -> str:
    diff = deadline_utc - now_utc()
    if diff <= timedelta(hours=3):
        return "🔴"
    if diff <= timedelta(hours=24):
        return "🟡"
    return "🟢"


def parse_deadline(raw: str, tz_name: str) -> datetime | None:
    text = raw.strip().lower()
    user_tz = ZoneInfo(tz_name)
    now_local = datetime.now(user_tz)

    absolute_formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]
    for fmt in absolute_formats:
        try:
            dt = datetime.strptime(text, fmt)
            if fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
                dt = dt.replace(hour=23, minute=59)
            local = dt.replace(tzinfo=user_tz)
            return local.astimezone(ZoneInfo("UTC"))
        except ValueError:
            continue

    if text == "завтра":
        target = (now_local + timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
        return target.astimezone(ZoneInfo("UTC"))
    if text == "послезавтра":
        target = (now_local + timedelta(days=2)).replace(hour=23, minute=59, second=0, microsecond=0)
        return target.astimezone(ZoneInfo("UTC"))

    rel = re.match(r"^через\s+(\d+)\s+(минут|минута|минуты|час|часа|часов|день|дня|дней)$", text)
    if rel:
        value = int(rel.group(1))
        unit = rel.group(2)
        if "минут" in unit or unit == "минута":
            delta = timedelta(minutes=value)
        elif "час" in unit:
            delta = timedelta(hours=value)
        else:
            delta = timedelta(days=value)
        return (now_local + delta).astimezone(ZoneInfo("UTC"))

    return None
