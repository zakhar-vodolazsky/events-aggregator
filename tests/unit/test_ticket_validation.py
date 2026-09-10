import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.main import create_app


@pytest.mark.parametrize("path", ["/api/tickets", "/api/tickets/"])
def test_ticket_validation(path):
    async def check():
        app = create_app()
        ticket_id = uuid4()
        tickets = SimpleNamespace(create=AsyncMock(return_value=ticket_id))
        app.state.container = SimpleNamespace(tickets=tickets)
        body = {
            "event_id": str(uuid4()),
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "ivan@example.com",
            "seat": "A1",
        }
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for invalid in (
                body | {"event_id": "not-a-uuid", "email": "x"},
                body | {"email": "x"},
                body | {"seat": "invalid"},
                {},
            ):
                response = await client.post(path, json=invalid)
                assert response.status_code == 400, response.text
                assert response.json()["detail"]
            response = await client.post(
                path, content="{", headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 400
            tickets.create.assert_not_awaited()

            response = await client.post(path, json=body)
            assert response.status_code == 201
            assert response.json() == {"ticket_id": str(ticket_id)}
            tickets.create.assert_awaited_once()

            assert (await client.get("/api/events?page=0")).status_code == 422

    asyncio.run(check())
