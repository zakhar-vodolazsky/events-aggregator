# Full API tests against an isolated PostgreSQL schema and a mocked provider

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import TypedDict
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.container import Container
from app.integrations.events_provider.client import EventsProviderClient
from app.main import create_app
from tests.integration.test_local_timestamps import apply_migration

pytestmark = pytest.mark.skipif(os.getenv("RUN_DB_TESTS") != "1", reason="Opt-in local DB test")


class PlacePayload(TypedDict):
    id: str
    name: str
    city: str
    address: str
    seats_pattern: str
    created_at: str
    changed_at: str


class EventPayload(TypedDict):
    id: str
    name: str
    place: PlacePayload
    event_time: str
    registration_deadline: str
    status: str
    number_of_visitors: int
    created_at: str
    changed_at: str
    status_changed_at: str


def sample_event(
    *,
    status: str = "published",
    event_time: str | None = None,
    registration_deadline: str | None = None,
) -> EventPayload:
    now = datetime.now(UTC)
    return {
        "id": str(uuid4()),
        "name": "Conference",
        "place": {
            "id": str(uuid4()),
            "name": "Hall",
            "city": "Moscow",
            "address": "Street 1",
            "seats_pattern": "A1-10,B1-20",
            "created_at": now.isoformat(),
            "changed_at": now.isoformat(),
        },
        "event_time": event_time
        if event_time is not None
        else (now + timedelta(days=5)).isoformat(),
        "registration_deadline": (
            registration_deadline
            if registration_deadline is not None
            else (now + timedelta(days=4)).isoformat()
        ),
        "status": status,
        "number_of_visitors": 0,
        "created_at": now.isoformat(),
        "changed_at": now.isoformat(),
        "status_changed_at": now.isoformat(),
    }


@asynccontextmanager
async def application():
    settings = get_settings().model_copy(update={"sync_enabled": False})
    url = make_url(settings.database_url)
    assert url.host in {"localhost", "127.0.0.1", "::1"}
    schema = "test_app_" + uuid4().hex
    admin = create_async_engine(url, hide_parameters=True)
    async with admin.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(
        url, hide_parameters=True, connect_args={"server_settings": {"search_path": schema}}
    )
    try:
        async with engine.begin() as conn:
            for file in (
                "57cc8980a41a_create_tables.py",
                "5c3bd19387d6_add_changed_at_triggers.py",
                "8e9a214c7b30_local_update_timestamps.py",
                "dd072595dfeb_add_sync_state_table.py",
                "f812d064ba31_registration_history.py",
            ):
                await conn.run_sync(apply_migration, file)
        provider = AsyncMock(spec=EventsProviderClient)
        provider.events.return_value = {"results": [], "next": None}
        provider.seats.return_value = {"seats": ["A1", "A2"]}
        provider.register.return_value = {"ticket_id": str(uuid4())}
        provider.unregister.return_value = {"success": True}
        container = Container(settings, engine=engine, provider=provider)
        app = create_app(container)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield client, container, provider
    finally:
        await engine.dispose()
        async with admin.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


def test_api_full_lifecycle():
    asyncio.run(full_lifecycle())


async def full_lifecycle():
    async with application() as (client, container, provider):
        first = sample_event()
        second = sample_event(event_time=(datetime.now(UTC) + timedelta(days=10)).isoformat())
        provider.events.side_effect = [
            {"results": [first], "next": "https://external.test/api/events/?cursor=abc"},
            {"results": [second], "next": None},
        ]
        assert (await client.get("/api/health")).json() == {"status": "ok"}
        assert (await client.get("/api/events")).json()["count"] == 0
        sync = await client.post("/api/sync/trigger")
        assert sync.status_code == 200, sync.text
        assert sync.json()["events_processed"] == 2
        assert provider.events.await_args_list[0].kwargs["changed_at"].isoformat() == "2000-01-01"
        assert provider.events.await_args_list[1].kwargs["cursor"] == "abc"
        page = (await client.get("/api/events/?page_size=1")).json()
        assert page["count"] == 2
        assert page["previous"] is None
        assert len(page["results"]) == 1
        assert "seats_pattern" not in page["results"][0]["place"]
        next_page = (await client.get(page["next"])).json()
        assert next_page["next"] is None
        assert next_page["previous"]
        cutoff = (datetime.now(UTC) + timedelta(days=7)).date()
        filtered = (await client.get(f"/api/events?date_from={cutoff}&page_size=1")).json()
        assert filtered["count"] == 1
        assert filtered["results"][0]["id"] == second["id"]
        detail = await client.get(f"/api/events/{first['id']}")
        assert detail.status_code == 200
        assert detail.json()["place"]["seats_pattern"] == "A1-10,B1-20"
        assert provider.events.await_count == 2  # all reads above used the database
        assert (await client.get("/api/events?page=0")).status_code == 422
        assert (await client.get("/api/events?date_from=bad")).status_code == 422
        assert (await client.get(f"/api/events/{uuid4()}")).status_code == 404

        seats_url = f"/api/events/{first['id']}/seats"
        for _ in range(2):
            assert (await client.get(seats_url)).json()["available_seats"] == ["A1", "A2"]
        assert provider.seats.await_count == 1
        body = {
            "event_id": first["id"],
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "ivan@example.com",
            "seat": "A1",
        }
        assert (await client.post("/api/tickets", json=body | {"email": "bad"})).status_code == 422
        assert (await client.post("/api/tickets", json=body | {"seat": "C1"})).status_code == 400
        created = await client.post("/api/tickets/", json=body)
        assert created.status_code == 201, created.text
        old_ticket = created.json()["ticket_id"]
        assert provider.seats.await_count == 2  # booking bypasses the display cache
        assert provider.register.await_count == 1
        assert (await client.post("/api/tickets", json=body)).status_code == 409
        assert provider.register.await_count == 1
        assert (await client.delete(f"/api/tickets/{old_ticket}/")).json() == {"success": True}
        new = await client.post("/api/tickets", json=body)
        assert new.status_code == 201, new.text
        assert new.json()["ticket_id"] != old_ticket
        assert (await client.delete(f"/api/tickets/{old_ticket}")).status_code == 409
        assert provider.unregister.await_count == 1
        assert (await client.delete(f"/api/tickets/{new.json()['ticket_id']}")).status_code == 200
        assert provider.unregister.await_count == 2
        # Provider reused the same ID, but each local registration has an independent lifetime.
        assert provider.unregister.await_args.args[1] == UUID(
            provider.register.return_value["ticket_id"]
        )

        provider.events.side_effect = None
        provider.events.return_value = {"results": [first, second], "next": None}
        assert (await client.post("/api/sync/trigger")).status_code == 200
        assert (await client.get("/api/events")).json()["count"] == 2
        assert (await container.worker.trigger(only_if_due=True))["status"] == "not_due"


def test_sync_rollback_and_lock():
    asyncio.run(sync_rollback_and_lock())


async def sync_rollback_and_lock():
    async with application() as (client, container, provider):
        original = sample_event()
        provider.events.return_value = {"results": [original], "next": None}
        assert (await client.post("/api/sync/trigger")).status_code == 200
        async with container.uow() as work:
            before = await work.sync.read()
        updated = original | {"name": "New name", "changed_at": datetime.now(UTC).isoformat()}
        provider.events.side_effect = [
            {"results": [updated], "next": "https://external.test/api/events/?cursor=abc"},
            httpx.ConnectError("Offline"),
        ]
        assert (await client.post("/api/sync/trigger")).status_code == 502
        assert (await client.get(f"/api/events/{original['id']}")).json()["name"] == "Conference"
        async with container.uow() as work:
            after = await work.sync.read()
        assert after.sync_status == "failed"
        assert after.last_changed_at == before.last_changed_at
        assert after.last_sync_time == before.last_sync_time
        calls = provider.events.await_count
        async with container.worker.lock() as acquired:
            assert acquired
            assert (await client.post("/api/sync/trigger")).json()["status"] == "already_running"
        assert provider.events.await_count == calls


def test_booking_business_rules():
    asyncio.run(booking_business_rules())


async def booking_business_rules():
    async with application() as (client, _container, provider):
        now = datetime.now(UTC)
        unpublished = sample_event(status="new")
        expired = sample_event(registration_deadline=(now - timedelta(hours=1)).isoformat())
        past = sample_event(event_time=(now - timedelta(hours=1)).isoformat())
        provider.events.return_value = {"results": [unpublished, expired, past], "next": None}
        assert (await client.post("/api/sync/trigger")).status_code == 200
        assert (await client.get(f"/api/events/{unpublished['id']}/seats")).status_code == 400
        for event in (unpublished, expired, past):
            body = {
                "event_id": event["id"],
                "first_name": "Ivan",
                "last_name": "Ivanov",
                "email": "ivan@example.com",
                "seat": "A1",
            }
            assert (await client.post("/api/tickets", json=body)).status_code == 400
        provider.seats.assert_not_awaited()
        provider.register.assert_not_awaited()


def test_concurrent_booking_and_cancel():
    asyncio.run(concurrent_booking_and_cancel())


async def concurrent_booking_and_cancel():
    async with application() as (client, _container, provider):
        event = sample_event()
        provider.events.return_value = {"results": [event], "next": None}
        assert (await client.post("/api/sync/trigger")).status_code == 200
        body = {
            "event_id": event["id"],
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "ivan@example.com",
            "seat": "A1",
        }
        replies = await asyncio.gather(*[client.post("/api/tickets", json=body) for _ in range(2)])
        assert sorted(r.status_code for r in replies) == [201, 409]
        assert provider.register.await_count == 1
        ticket = next(r.json()["ticket_id"] for r in replies if r.status_code == 201)
        replies = await asyncio.gather(*[client.delete(f"/api/tickets/{ticket}") for _ in range(2)])
        assert sorted(r.status_code for r in replies) == [200, 409]
        assert provider.unregister.await_count == 1


def test_sync_preserves_newer_records():
    asyncio.run(sync_preserves_newer_records())


async def sync_preserves_newer_records():
    async with application() as (client, container, provider):
        event = sample_event()
        provider.events.return_value = {"results": [event], "next": None}
        assert (await client.post("/api/sync/trigger")).status_code == 200
        old_time = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        older = event | {
            "name": "Older name",
            "changed_at": old_time,
            "place": event["place"] | {"name": "Older hall", "changed_at": old_time},
        }
        provider.events.return_value = {"results": [older], "next": None}
        assert (await client.post("/api/sync/trigger")).status_code == 200
        detail = (await client.get(f"/api/events/{event['id']}")).json()
        assert detail["name"] == "Conference"
        assert detail["place"]["name"] == "Hall"
        async with container.uow() as work:
            state = await work.sync.read()
        assert state.last_changed_at == datetime.fromisoformat(event["changed_at"])


def test_provider_failure_does_not_create_ticket():
    asyncio.run(provider_failure_does_not_create_ticket())


async def provider_failure_does_not_create_ticket():
    async with application() as (client, container, provider):
        event = sample_event()
        provider.events.return_value = {"results": [event], "next": None}
        assert (await client.post("/api/sync/trigger")).status_code == 200
        response = httpx.Response(
            500,
            text="<html>private error</html>",
            request=httpx.Request("POST", "https://provider.test"),
        )
        provider.register.side_effect = httpx.HTTPStatusError(
            "Provider failure", request=response.request, response=response
        )
        body = {
            "event_id": event["id"],
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "ivan@example.com",
            "seat": "A1",
        }
        reply = await client.post("/api/tickets", json=body)
        assert reply.status_code == 502
        assert "private error" not in reply.text
        async with container.uow() as work:
            assert not await work.tickets.active_seat(UUID(event["id"]), "A1")
