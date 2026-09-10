from contextlib import asynccontextmanager

from sqlalchemy import text

# Stable shared key identifies the event synchronization lock in PostgreSQL.
SYNC_LOCK = 76321408


@asynccontextmanager
async def synchronization_lock(engine):
    async with engine.connect() as connection:
        async with connection.begin():
            acquired = await connection.scalar(
                text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": SYNC_LOCK}
            )
            yield acquired
