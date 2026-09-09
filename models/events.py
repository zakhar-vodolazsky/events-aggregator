import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base
from models.enums import EventStatus

if TYPE_CHECKING:
    from models import Location, Ticket


class Event(Base):
    __tablename__ = "events"

    uuid: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    location_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("locations.uuid", ondelete="SET NULL"), index=True
    )

    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registration_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[EventStatus] = mapped_column(
        String, nullable=False, default=EventStatus.PUBLISHED.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    location: Mapped[Location] = relationship("Location", back_populates="events")
    tickets: Mapped[list[Ticket]] = relationship("Ticket", back_populates="event")
