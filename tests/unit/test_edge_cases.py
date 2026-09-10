# Edge test cases
import asyncio
from datetime import date
from typing import cast
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from app.cache.seats import SeatsCache
from app.domain.ports import Provider
from app.domain.schemas import ProviderError
from app.integrations.events_provider.client import EventsProviderClient
from app.integrations.events_provider.paginator import EventsPaginator


def test_provider_cursor():
    client = EventsProviderClient("https://provider.test", "test")
    response = httpx.Response(
        200,
        json={"results": [], "next": None},
        request=httpx.Request("GET", "https://provider.test/api/events/"),
    )
    with patch(
        "app.integrations.events_provider.client.httpx.AsyncClient.get",
        new_callable=AsyncMock,
        return_value=response,
    ) as get:
        asyncio.run(client.events(date(2000, 1, 1), "a+b="))
    assert get.await_args is not None
    assert get.await_args.kwargs["params"] == {"changed_at": "2000-01-01", "cursor": "a+b="}


def test_reads_retry_network_errors():
    client = EventsProviderClient("https://provider.test", "test")
    response = httpx.Response(
        200, json={"seats": []}, request=httpx.Request("GET", "https://provider.test")
    )
    with patch(
        "app.integrations.events_provider.client.httpx.AsyncClient.get",
        new_callable=AsyncMock,
        side_effect=[httpx.ConnectError("offline"), response],
    ) as get:
        with patch("app.integrations.events_provider.client.asyncio.sleep", new_callable=AsyncMock):
            assert asyncio.run(client.seats(uuid4())) == {"seats": []}
    assert get.await_count == 2


def test_registration_timeout_is_not_retried():
    client = EventsProviderClient("https://provider.test", "test")
    with patch(
        "app.integrations.events_provider.client.httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ReadTimeout("timeout"),
    ) as post:
        with pytest.raises(httpx.ReadTimeout):
            asyncio.run(client.register(uuid4(), "Ivan", "Ivanov", "i@example.com", "A1"))
    assert post.await_count == 1


def test_invalid_json_becomes_provider_error():
    client = EventsProviderClient("https://provider.test", "test")
    response = httpx.Response(
        200, text="<html>error</html>", request=httpx.Request("GET", "https://provider.test")
    )
    with patch(
        "app.integrations.events_provider.client.httpx.AsyncClient.get",
        new_callable=AsyncMock,
        return_value=response,
    ):
        with pytest.raises(ProviderError):
            asyncio.run(client.seats(uuid4()))


@pytest.mark.parametrize(
    "next_url", ["https://provider.test/?cursor=abc", "https://provider.test/"]
)
def test_paginator_rejects_bad_navigation(next_url):
    provider = AsyncMock(spec=EventsProviderClient)
    provider.events.return_value = {"results": [], "next": next_url}

    async def collect():
        return [
            event
            async for event in EventsPaginator(
                cast(Provider, cast(object, provider)), date(2000, 1, 1)
            )
        ]

    with pytest.raises(ProviderError):
        asyncio.run(collect())
    assert provider.events.await_count <= 2


def test_cache_ttl_and_invalidation():
    async def run():
        cache = SeatsCache()
        provider = AsyncMock(spec=EventsProviderClient)
        provider.seats.return_value = {"seats": ["A1"]}
        event_id = uuid4()
        with patch("app.cache.seats.monotonic", return_value=0):
            seats = await cache.get(event_id, cast(Provider, cast(object, provider)))
            seats.clear()  # callers cannot mutate the cached value
        with patch("app.cache.seats.monotonic", return_value=29):
            assert await cache.get(event_id, cast(Provider, cast(object, provider))) == ["A1"]
        assert provider.seats.await_count == 1
        with patch("app.cache.seats.monotonic", return_value=30):
            await cache.get(event_id, cast(Provider, cast(object, provider)))
        assert provider.seats.await_count == 2
        cache.invalidate(event_id)
        await cache.get(event_id, cast(Provider, cast(object, provider)))
        assert provider.seats.await_count == 3

    asyncio.run(run())


def test_cache_does_not_restore_invalidated_inflight_response():
    async def run():
        cache = SeatsCache()
        event_id = uuid4()
        provider = AsyncMock(spec=EventsProviderClient)

        async def fetch(_event_id):
            cache.invalidate(event_id)
            return {"seats": ["A1"]}

        provider.seats.side_effect = fetch
        await cache.get(event_id, cast(Provider, cast(object, provider)))
        assert event_id not in cache.values

    asyncio.run(run())
