from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PlaceResponse(BaseModel):
    id: UUID
    name: str
    city: str | None
    address: str | None


class PlaceDetail(PlaceResponse):
    seats_pattern: str | None


class EventResponse(BaseModel):
    id: UUID
    name: str
    place: PlaceResponse
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventDetail(EventResponse):
    place: PlaceDetail


class EventsPage(BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[EventResponse]
