import asyncio
import logging

from aiogram import Bot, Dispatcher

from handlers.admin import router as admin_router
from handlers.archive import router as archive_router
from handlers.create_order import router as create_order_router
from handlers.menu import router as menu_router
from handlers.orders import router as orders_router
from handlers.scheduler import setup_scheduler, shutdown_scheduler
from handlers.user_settings import router as user_settings_router

from config import get_settings
from db import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


async def main() -> None:
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_routers(
        create_order_router, menu_router, orders_router, user_settings_router, archive_router, admin_router
    )

    await db.connect()
    await db.init_db()
    logger.info("Database ready")

    try:
        try:
            logger.info("Connecting to Telegram (delete_webhook)...")
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            logger.exception(
                "Не удалось связаться с Telegram (delete_webhook). Проверьте BOT_TOKEN и доступ к api.telegram.org"
            )
            raise
        logger.info("Webhook cleared, starting long polling")
        await setup_scheduler(bot)
        await dp.start_polling(bot)
    finally:
        await shutdown_scheduler()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
