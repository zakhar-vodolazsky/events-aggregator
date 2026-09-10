import re
from datetime import UTC, datetime
from uuid import UUID

from app.cache.seats import SeatsCache
from app.domain.ports import Provider, UnitOfWorkFactory
from app.domain.schemas import BusinessError, ProviderError, Registration


def validate_seat(seat: str, pattern: str | None) -> None:
    if not pattern:
        raise BusinessError("Event has no seating scheme")
    for section in pattern.split(","):
        match = re.fullmatch(r"([A-Z])([1-9][0-9]*)-([1-9][0-9]*)", section.strip())
        if not match:
            raise BusinessError("Event has an invalid seating scheme")
        letter, first, last = match.groups()
        if seat[0] == letter and int(first) <= int(seat[1:]) <= int(last):
            return
    raise BusinessError("Seat does not exist at this venue")


class TicketService:
    def __init__(self, uow: UnitOfWorkFactory, provider: Provider, cache: SeatsCache):
        self.uow = uow
        self.provider = provider
        self.cache = cache

    async def create(self, data: Registration) -> UUID:
        async with self.uow() as work:
            event = await work.events.find(data.event_id, lock=True)
            if event is None:
                raise BusinessError("Event not found", 404)
            if event.status != "published":
                raise BusinessError("Event is not published")
            now = datetime.now(UTC)
            if now >= event.registration_deadline or now >= event.event_time:
                raise BusinessError("Registration is closed")
            validate_seat(data.seat, event.place.seats_pattern)
            if await work.tickets.active_seat(data.event_id, data.seat):
                raise BusinessError("Seat is already registered", 409)
            seats = await self.cache.get(data.event_id, self.provider, fresh=True)
            if data.seat not in seats:
                raise BusinessError("Seat is not available", 409)
            try:
                response = await self.provider.register(**data.model_dump())
                try:
                    provider_id = UUID(response["ticket_id"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ProviderError("Invalid registration response from provider", 502) from exc
                return await work.tickets.create(data, provider_id)
            finally:
                self.cache.invalidate(data.event_id)

    async def cancel(self, ticket_id: UUID) -> None:
        async with self.uow() as work:
            ticket = await work.tickets.find(ticket_id)
            if ticket is None:
                raise BusinessError("Ticket not found", 404)
            # Lock event first for both create and cancel, then refresh ticket after waiting.
            event = await work.events.find(ticket.event_id, lock=True)
            ticket = await work.tickets.find(ticket_id, lock=True)

            if ticket is None:
                raise BusinessError("Ticket not found", 404)

            if ticket.is_revoked:
                raise BusinessError("Registration is already cancelled", 409)

            if event is None:
                raise BusinessError("Event not found", 404)
            if datetime.now(UTC) >= event.event_time:
                raise BusinessError("Cannot cancel a past event")
            try:
                result = await self.provider.unregister(ticket.event_id, ticket.provider_ticket_id)
                # noinspection PySimplifyBooleanCheck
                if result.get("success") is not True:
                    raise ProviderError("Invalid cancellation response from provider", 502)
                await work.tickets.revoke(ticket_id)
            finally:
                self.cache.invalidate(ticket.event_id)
