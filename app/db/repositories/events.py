from datetime import UTC, date, datetime, time
from typing import cast
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Event
from app.db.models.enums import EventStatus
from app.domain.schemas import EventData


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find(self, event_id: UUID, *, lock: bool = False) -> EventData | None:
        query = select(Event).where(Event.id == event_id).options(selectinload(Event.place))
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        event = await self.session.scalar(query)
        return EventData.model_validate(event) if event else None

    async def list(self, date_from: date | None, page: int, page_size: int):
        filters = []
        if date_from:
            filters.append(Event.event_time >= datetime.combine(date_from, time.min, tzinfo=UTC))
        count = await self.session.scalar(select(func.count()).select_from(Event).where(*filters))
        query = (
            select(Event)
            .where(*filters)
            .options(selectinload(Event.place))
            .order_by(Event.event_time, Event.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        events = (await self.session.scalars(query)).all()
        return count, [EventData.model_validate(event) for event in events]

    async def upsert(self, event: EventData) -> None:
        values = event.model_dump(exclude={"place"}) | {"place_id": event.place.id}
        statement = insert(Event).values(**values)
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[Event.id],
                set_={key: getattr(statement.excluded, key) for key in values if key != "id"},
                where=or_(
                    Event.changed_at.is_(None), Event.changed_at < statement.excluded.changed_at
                ),
            )
        )

    async def get(self, event_id: UUID) -> Event | None:
        result = await self.session.get(Event, event_id)
        return cast(Event | None, result)

    async def save(
        self,
        *,
        event_id: UUID,
        place_id: UUID,
        name: str,
        event_time: datetime,
        registration_deadline: datetime,
        status: EventStatus,
        number_of_visitors: int,
        created_at: datetime,
        changed_at: datetime,
        status_changed_at: datetime,
    ) -> Event:
        event = await self.get(event_id)

        if event is None:
            event = Event(id=event_id)
            self.session.add(event)

        event.place_id = place_id
        event.name = name
        event.event_time = event_time
        event.registration_deadline = registration_deadline
        event.status = status
        event.number_of_visitors = number_of_visitors
        event.created_at = created_at
        event.changed_at = changed_at
        event.status_changed_at = status_changed_at

        await self.session.flush()
        return event
