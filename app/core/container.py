from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine

from app.cache.seats import SeatsCache
from app.core.config import Settings
from app.db.session import create_engine, create_session_factory
from app.db.unit_of_work import SqlUnitOfWork
from app.domain.ports import Provider
from app.integrations.events_provider.client import EventsProviderClient
from app.services.events import EventService
from app.services.sync import SyncService
from app.services.tickets import TicketService
from app.workers.sync import SyncWorker


class Container:
    # Initialize application dependencies

    def __init__(
        self,
        settings: Settings,
        *,
        engine: AsyncEngine | None = None,
        provider: Provider | None = None,
    ):
        self.settings = settings
        self.engine = engine if engine is not None else create_engine(settings.database_url)
        self.sessions = create_session_factory(self.engine)
        self.provider = (
            provider
            if provider is not None
            else EventsProviderClient(
                settings.events_provider_base_url, settings.events_provider_api_key
            )
        )
        self.cache = SeatsCache()
        self.events = EventService(self.uow, self.provider, self.cache)
        self.tickets = TicketService(self.uow, self.provider, self.cache)
        self.sync = SyncService(self.uow, self.provider, self.cache)
        self.worker = SyncWorker(settings, self.engine, self.uow, self.sync)

    def uow(self):
        return SqlUnitOfWork(self.sessions)

    @asynccontextmanager
    async def lifespan(self):
        try:
            async with self.worker.lifespan():
                yield
        finally:
            await self.engine.dispose()
