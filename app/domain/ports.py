# Interfaces used by business logic; implemented by repositories and infrastructure

from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import Protocol, Self
from uuid import UUID

from app.domain.schemas import EventData, PlaceData, Registration, SyncData, TicketData


class Provider(Protocol):
    async def events(self, changed_at: date, cursor: str | None = None) -> dict: ...
    async def seats(self, event_id: UUID) -> dict: ...

    async def register(
        self,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> dict: ...
    async def unregister(self, event_id: UUID, ticket_id: UUID) -> dict: ...


class Events(Protocol):
    async def find(self, event_id: UUID, *, lock: bool = False) -> EventData | None: ...
    async def list(self, date_from: date | None, page: int, page_size: int) -> tuple[int, list]: ...
    async def upsert(self, event: EventData) -> None: ...


class Places(Protocol):
    async def upsert(self, place: PlaceData) -> None: ...


class Tickets(Protocol):
    async def find(self, ticket_id: UUID, *, lock: bool = False) -> TicketData | None: ...
    async def create(self, data: Registration, provider_ticket_id: UUID) -> UUID: ...
    async def revoke(self, ticket_id: UUID) -> None: ...
    async def active_seat(self, event_id: UUID, seat: str) -> bool: ...


class SyncStates(Protocol):
    async def read(self) -> SyncData: ...
    async def update(
        self,
        status: str,
        *,
        changed_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None: ...


class UnitOfWork(Protocol):
    events: Events
    places: Places
    tickets: Tickets
    sync: SyncStates

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...


class EventStream(Protocol):
    def __aiter__(self) -> AsyncIterator[dict]: ...
