import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base
from models.enums import EventStatus

if TYPE_CHECKING:
    from models import Place, Ticket


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("places.id", ondelete="SET NULL"), index=True
    )
    number_of_visitors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

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
    changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    place: Mapped[Place] = relationship("Place", back_populates="events")
    tickets: Mapped[list[Ticket]] = relationship("Ticket", back_populates="event")
