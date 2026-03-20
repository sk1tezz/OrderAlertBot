import asyncpg

from config import get_settings


class Database:
    def __init__(self) -> None:
        s = get_settings()
        self._dsn = f"postgresql://{s.db_user}:{s.db_password}@{s.db_host}:{s.db_port}/{s.db_name}"
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def init_db(self) -> None:
        await self.connect()
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    timezone VARCHAR(50) NOT NULL DEFAULT 'Europe/Moscow',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    notify_24h BOOLEAN NOT NULL DEFAULT TRUE,
                    notify_3h BOOLEAN NOT NULL DEFAULT TRUE,
                    notify_1h BOOLEAN NOT NULL DEFAULT TRUE,
                    page_size SMALLINT NOT NULL DEFAULT 5,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    deadline TIMESTAMPTZ NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders_log (
                    id BIGSERIAL PRIMARY KEY,
                    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    remind_type VARCHAR(20) NOT NULL,
                    is_sent BOOLEAN NOT NULL DEFAULT FALSE,
                    sent_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )


db = Database()
