import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from models import Event, Guest


class Ticket(Base):
    __tablename__ = "tickets"

    uuid: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)

    event_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("events.uuid", ondelete="CASCADE"), nullable=False, index=True
    )
    guest_uuid: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("guests.uuid", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    event: Mapped[Event] = relationship("Event", back_populates="tickets")
    guest: Mapped[Guest] = relationship("Guest", back_populates="tickets")
