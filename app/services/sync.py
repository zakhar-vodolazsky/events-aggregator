import asyncio
import logging
from datetime import UTC, date, datetime

from pydantic import ValidationError

from app.cache.seats import SeatsCache
from app.domain.ports import Provider, UnitOfWorkFactory
from app.domain.schemas import EventData, ProviderError
from app.integrations.events_provider.paginator import EventsPaginator

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, uow: UnitOfWorkFactory, provider: Provider, cache: SeatsCache):
        self.uow = uow
        self.provider = provider
        self.cache = cache

    async def run(self) -> dict:
        async with self.uow() as work:
            state = await work.sync.read()
            watermark = state.last_changed_at
            await work.sync.update("running")
        since = watermark.astimezone(UTC).date() if watermark else date(2000, 1, 1)
        count = 0
        logger.info("Event synchronization started from %s", since)
        try:
            async with self.uow() as work:
                async for raw in EventsPaginator(self.provider, since):
                    try:
                        event = EventData.model_validate(raw)
                    except ValidationError as exc:
                        raise ProviderError("Invalid event data from provider", 502) from exc
                    await work.places.upsert(event.place)
                    await work.events.upsert(event)
                    if watermark is None or event.changed_at > watermark:
                        watermark = event.changed_at
                    count += 1
                await work.sync.update(
                    "success", changed_at=watermark, completed_at=datetime.now(UTC)
                )
        except (Exception, asyncio.CancelledError) as exc:
            logger.error("Event synchronization failed (%s)", type(exc).__name__)
            async with self.uow() as work:
                await work.sync.update("failed")
            raise
        self.cache.clear()
        logger.info("Event synchronization completed: %s events", count)
        return {"status": "success", "events_processed": count}
