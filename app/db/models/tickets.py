import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models import Base

if TYPE_CHECKING:
    from app.db.models import Event


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index(
            "uq_ticket_active_seat",
            "event_id",
            "seat",
            unique=True,
            postgresql_where=text("NOT is_revoked"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    provider_ticket_id: Mapped[uuid.UUID] = mapped_column(UUID, nullable=False)

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )

    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, index=True)

    seat: Mapped[str] = mapped_column(String, nullable=False)

    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    event: Mapped[Event] = relationship("Event", back_populates="tickets")
