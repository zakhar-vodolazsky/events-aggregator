from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.api.schemas import EventDetail, EventsPage
from app.domain.schemas import Registration

router = APIRouter(prefix="/api")


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/sync/trigger")
async def trigger_sync(request: Request):
    return await request.app.state.container.worker.trigger()


@router.get("/events", response_model=EventsPage)
async def events(
    request: Request,
    date_from: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000)] = 20,
):
    count, results = await request.app.state.container.events.list(date_from, page, page_size)

    def page_url(number):
        return str(request.url.include_query_params(page=number, page_size=page_size))

    return {
        "count": count,
        "next": page_url(page + 1) if page * page_size < count else None,
        "previous": page_url(page - 1) if page > 1 else None,
        "results": [event.model_dump() for event in results],
    }


@router.get("/events/{event_id}", response_model=EventDetail)
async def event_detail(event_id: UUID, request: Request):
    return (await request.app.state.container.events.detail(event_id)).model_dump()


@router.get("/events/{event_id}/seats")
async def event_seats(event_id: UUID, request: Request):
    seats = await request.app.state.container.events.seats(event_id)
    return {"event_id": event_id, "available_seats": seats}


@router.post("/tickets", status_code=201)
async def create_ticket(data: Registration, request: Request):
    return {"ticket_id": await request.app.state.container.tickets.create(data)}


@router.delete("/tickets/{ticket_id}")
async def cancel_ticket(ticket_id: UUID, request: Request):
    await request.app.state.container.tickets.cancel(ticket_id)
    return {"success": True}


# Both course URL styles work without redirecting mutation requests.
for route in list(router.routes):
    router.add_api_route(
        route.path.removeprefix("/api") + "/",
        route.endpoint,
        methods=list(route.methods),
        response_model=route.response_model,
        status_code=route.status_code,
        include_in_schema=False,
    )
