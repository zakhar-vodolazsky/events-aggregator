from __future__ import annotations

import builtins
from datetime import date
from uuid import UUID

from app.cache.seats import SeatsCache
from app.domain.ports import Provider, UnitOfWorkFactory
from app.domain.schemas import BusinessError, EventData


class EventService:
    def __init__(self, uow: UnitOfWorkFactory, provider: Provider, cache: SeatsCache):
        self.uow = uow
        self.provider = provider
        self.cache = cache

    async def list(self, date_from: date | None, page: int, page_size: int):
        async with self.uow() as work:
            return await work.events.list(date_from, page, page_size)

    async def detail(self, event_id: UUID) -> EventData:
        async with self.uow() as work:
            event = await work.events.find(event_id)
            if event is None:
                raise BusinessError("Event not found", 404)
            return event

    async def seats(self, event_id: UUID) -> builtins.list[str]:
        event = await self.detail(event_id)
        if event.status != "published":
            raise BusinessError("Event is not published")
        return await self.cache.get(event_id, self.provider)
