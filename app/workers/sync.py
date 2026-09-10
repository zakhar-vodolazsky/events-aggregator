import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime

from app.db.locks import synchronization_lock

logger = logging.getLogger(__name__)


class SyncWorker:
    def __init__(self, settings, engine, uow, sync):
        self.settings = settings
        self.engine = engine
        self.uow = uow
        self.sync = sync

    def lock(self):
        return synchronization_lock(self.engine)

    async def trigger(self, *, only_if_due=False):
        async with self.lock() as acquired:
            if not acquired:
                return {"status": "already_running"}
            if only_if_due:
                async with self.uow() as work:
                    state = await work.sync.read()
                if state.last_sync_time:
                    elapsed = (datetime.now(UTC) - state.last_sync_time).total_seconds()
                    if elapsed < self.settings.sync_interval_seconds:
                        return {"status": "not_due"}
            return await self.sync.run()

    async def run(self):
        while True:
            try:
                await self.trigger(only_if_due=True)
            except Exception as exc:
                logger.error("Background synchronization error: %s", type(exc).__name__)
            await asyncio.sleep(60)

    @asynccontextmanager
    async def lifespan(self):
        task = None
        if self.settings.sync_enabled:
            task = asyncio.create_task(self.run(), name="events-sync")
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
