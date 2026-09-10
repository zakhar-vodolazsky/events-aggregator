from app.db.repositories.events import EventRepository
from app.db.repositories.places import PlaceRepository
from app.db.repositories.sync_state import SyncStateRepository
from app.db.repositories.tickets import TicketRepository


class SqlUnitOfWork:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()
        await self.session.begin()
        self.events = EventRepository(self.session)
        self.places = PlaceRepository(self.session)
        self.tickets = TicketRepository(self.session)
        self.sync = SyncStateRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
