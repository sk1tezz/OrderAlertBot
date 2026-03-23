from __future__ import annotations

import asyncio
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_STOPPED

from config import get_settings
from db import db
from utils.models import OrderStatus, ReminderType
from utils.services import ACTIVE_STATUSES, ARCHIVE_STATUSES, format_left, now_utc

from .common import deadline_to_user_string

settings = get_settings()
scheduler = AsyncIOScheduler()
_bot = None
_tick_lock = asyncio.Lock()


async def reminder_tick():
    async with _tick_lock:
        assert db.pool is not None
        now = now_utc()
        orders = await db.pool.fetch("SELECT * FROM orders WHERE status = ANY($1::text[])", ACTIVE_STATUSES)
        for order in orders:
            user = await db.pool.fetchrow("SELECT * FROM users WHERE id = $1", order["user_id"])
            left = order["deadline"] - now
            new_status = (
                OrderStatus.OVERDUE.value
                if left.total_seconds() < 0
                else OrderStatus.UPCOMING.value
                if left <= timedelta(hours=24)
                else OrderStatus.ACTIVE.value
            )
            if new_status != order["status"]:
                await db.pool.execute("UPDATE orders SET status = $1, updated_at = NOW() WHERE id = $2", new_status, order["id"])
            logs = await db.pool.fetch("SELECT * FROM reminders_log WHERE order_id = $1 AND is_sent = TRUE", order["id"])
            sent_types = {r["remind_type"] for r in logs}
            send_window = timedelta(seconds=settings.reminder_check_interval)
            plan = [
                (ReminderType.H24.value, timedelta(hours=24), user["notify_24h"]),
                (ReminderType.H3.value, timedelta(hours=3), user["notify_3h"]),
                (ReminderType.H1.value, timedelta(hours=1), user["notify_1h"]),
                (ReminderType.DEADLINE.value, timedelta(seconds=0), True),
            ]
            for remind_type, threshold, enabled in plan:
                if not enabled or remind_type in sent_types:
                    continue
                if threshold.total_seconds() == 0:
                    should_send = left <= timedelta(seconds=0) and left >= -send_window
                else:
                    should_send = left <= threshold and left >= threshold - send_window

                if should_send:
                    await _bot.send_message(
                        user["telegram_id"],
                        "Напоминание!\n\n"
                        f"{order['title']}\n"
                        f"Дедлайн: {deadline_to_user_string(order['deadline'], user['timezone'])}\n"
                        f"Осталось: {format_left(left)}",
                    )
                    await db.pool.execute(
                        "INSERT INTO reminders_log (order_id, remind_type, is_sent, sent_at) VALUES ($1, $2, TRUE, NOW())",
                        order["id"],
                        remind_type,
                    )
            if left < timedelta(seconds=0):
                overdue_logs = [r for r in logs if r["remind_type"] == ReminderType.OVERDUE.value]
                should_send = not overdue_logs or (now - overdue_logs[-1]["sent_at"]) >= timedelta(hours=24)
                if should_send:
                    await _bot.send_message(
                        user["telegram_id"],
                        "Заказ просрочен!\n\n"
                        f"{order['title']}\n"
                        f"Дедлайн был: {deadline_to_user_string(order['deadline'], user['timezone'])}\n"
                        f"Просрочен на: {format_left(now - order['deadline'])}",
                    )
                    await db.pool.execute(
                        "INSERT INTO reminders_log (order_id, remind_type, is_sent, sent_at) VALUES ($1, $2, TRUE, NOW())",
                        order["id"],
                        ReminderType.OVERDUE.value,
                    )
        await db.pool.execute(
            "DELETE FROM orders WHERE status = ANY($1::text[]) AND updated_at < NOW() - INTERVAL '90 days'",
            ARCHIVE_STATUSES,
        )


async def setup_scheduler(bot):
    global _bot
    _bot = bot

    scheduler.add_job(
        reminder_tick,
        "interval",
        seconds=settings.reminder_check_interval,
        id="reminder_tick",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()


async def shutdown_scheduler():
    if scheduler.state != STATE_STOPPED:
        scheduler.shutdown(wait=False)
