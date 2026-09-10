from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ticket
from app.domain.schemas import Registration, TicketData


class TicketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find(self, ticket_id: UUID, *, lock: bool = False) -> TicketData | None:
        query = select(Ticket).where(Ticket.id == ticket_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        ticket = await self.session.scalar(query)
        return TicketData.model_validate(ticket) if ticket else None

    async def create(self, data: Registration, provider_ticket_id: UUID) -> UUID:
        ticket_id = uuid4()
        self.session.add(
            Ticket(id=ticket_id, provider_ticket_id=provider_ticket_id, **data.model_dump())
        )
        await self.session.flush()
        return ticket_id

    async def revoke(self, ticket_id: UUID) -> None:
        ticket = await self.session.get(Ticket, ticket_id)
        ticket.is_revoked = True
        await self.session.flush()

    async def active_seat(self, event_id: UUID, seat: str) -> bool:
        return (
            await self.session.scalar(
                select(Ticket.id).where(
                    Ticket.event_id == event_id, Ticket.seat == seat, Ticket.is_revoked.is_(False)
                )
            )
        ) is not None
