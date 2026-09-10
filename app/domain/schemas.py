from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, StringConstraints


class DataModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlaceData(DataModel):
    id: UUID
    name: str
    city: str | None = None
    address: str | None = None
    seats_pattern: str | None = None
    created_at: AwareDatetime
    changed_at: AwareDatetime


class EventData(DataModel):
    id: UUID
    name: str
    place: PlaceData
    event_time: AwareDatetime
    registration_deadline: AwareDatetime
    status: str
    number_of_visitors: int = Field(ge=0)
    created_at: AwareDatetime
    changed_at: AwareDatetime
    status_changed_at: AwareDatetime


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Seat = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Z][1-9][0-9]*$")]


class Registration(BaseModel):
    event_id: UUID
    first_name: Name
    last_name: Name
    email: EmailStr
    seat: Seat


class TicketData(DataModel):
    id: UUID
    provider_ticket_id: UUID
    event_id: UUID
    seat: str
    is_revoked: bool


class SyncData(DataModel):
    last_sync_time: datetime | None = None
    last_changed_at: datetime | None = None
    sync_status: str = "pending"


class BusinessError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ProviderError(BusinessError):
    pass
