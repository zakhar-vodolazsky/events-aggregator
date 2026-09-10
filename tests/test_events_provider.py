import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
import pytest

from events_provider import EventsProviderClient


def test_events():
    expected = {
        "next": None,
        "previous": None,
        "results": [],
    }

    response = httpx.Response(
        status_code=200,
        json=expected,
        request=httpx.Request(
            "GET",
            "https://provider.test/api/events/",
        ),
    )

    client = EventsProviderClient(
        base_url="https://provider.test/",
        api_key="test-key",
    )

    with patch(
        "events_provider.httpx.AsyncClient.get",
        new_callable=AsyncMock,
        return_value=response,
    ) as mock_get:
        result = asyncio.run(client.events(date(2000, 1, 1)))

    assert result == expected

    mock_get.assert_awaited_once_with(
        "https://provider.test/api/events/",
        headers={"x-api-key": "test-key"},
        params={"changed_at": "2000-01-01"},
    )


def test_events_unauthorized():
    response = httpx.Response(
        status_code=401,
        json={"detail": "Invalid API key"},
        request=httpx.Request(
            "GET",
            "https://provider.test/api/events/",
        ),
    )

    client = EventsProviderClient(
        base_url="https://provider.test",
        api_key="wrong-key",
    )

    with patch(
        "events_provider.httpx.AsyncClient.get",
        new_callable=AsyncMock,
        return_value=response,
    ):
        with pytest.raises(httpx.HTTPStatusError) as error:
            asyncio.run(client.events(date(2000, 1, 1)))

    assert error.value.response.status_code == 401


def test_seats():
    event_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    url = f"https://provider.test/api/events/{event_id}/seats/"
    expected = {"seats": ["A1", "B2"]}

    response = httpx.Response(
        status_code=200,
        json=expected,
        request=httpx.Request("GET", url),
    )

    client = EventsProviderClient(
        base_url="https://provider.test",
        api_key="test-key",
    )

    with patch(
        "events_provider.httpx.AsyncClient.get",
        new_callable=AsyncMock,
        return_value=response,
    ) as mock_get:
        result = asyncio.run(client.seats(event_id))

    assert result == expected
    mock_get.assert_awaited_once_with(
        url,
        headers={"x-api-key": "test-key"},
    )


def test_register():
    event_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    ticket_id = "1fed0122-b675-42e2-8ae7-49bfb53e8d7f"
    url = f"https://provider.test/api/events/{event_id}/register/"
    expected = {"ticket_id": ticket_id}

    participant = {
        "first_name": "Иван",
        "last_name": "Иванов",
        "email": "ivan@example.com",
        "seat": "A15",
    }

    response = httpx.Response(
        status_code=201,
        json=expected,
        request=httpx.Request("POST", url),
    )

    client = EventsProviderClient(
        base_url="https://provider.test",
        api_key="test-key",
    )

    with patch(
        "events_provider.httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=response,
    ) as mock_post:
        result = asyncio.run(client.register(event_id=event_id, **participant))

    assert result == expected
    mock_post.assert_awaited_once_with(
        url,
        headers={"x-api-key": "test-key"},
        json=participant,
    )


def test_unregister():
    event_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    ticket_id = UUID("1fed0122-b675-42e2-8ae7-49bfb53e8d7f")
    url = f"https://provider.test/api/events/{event_id}/unregister/"
    expected = {"success": True}

    response = httpx.Response(
        status_code=200,
        json=expected,
        request=httpx.Request("DELETE", url),
    )

    client = EventsProviderClient(
        base_url="https://provider.test",
        api_key="test-key",
    )

    with patch(
        "events_provider.httpx.AsyncClient.request",
        new_callable=AsyncMock,
        return_value=response,
    ) as mock_request:
        result = asyncio.run(client.unregister(event_id, ticket_id))

    assert result == expected
    mock_request.assert_awaited_once_with(
        "DELETE",
        url,
        headers={"x-api-key": "test-key"},
        json={"ticket_id": str(ticket_id)},
    )
