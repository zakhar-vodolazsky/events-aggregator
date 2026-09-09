import uuid
from typing import TYPE_CHECKING

from sqlalchemy import UUID, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from models import Ticket


class Guest(Base):
    __tablename__ = "guests"

    uuid: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    tickets: Mapped[list[Ticket]] = relationship("Ticket", back_populates="guest")
