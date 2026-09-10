import asyncio
from datetime import date
from unittest.mock import AsyncMock, call

from events_paginator import EventsPaginator
from events_provider import EventsProviderClient


def test_paginator_two_pages():
    first_event = {"id": "event-1", "name": "Первое событие"}
    second_event = {"id": "event-2", "name": "Второе событие"}
    third_event = {"id": "event-3", "name": "Третье событие"}

    client = AsyncMock(spec=EventsProviderClient)
    client.events.side_effect = [
        {
            "results": [first_event, second_event],
            "next": ("https://provider.test/api/events/?changed_at=2000-01-01&cursor=abc"),
        },
        {
            "results": [third_event],
            "next": None,
        },
    ]

    changed_at = date(2000, 1, 1)

    async def collect_events():
        return [event async for event in EventsPaginator(client, changed_at)]

    result = asyncio.run(collect_events())

    assert result == [first_event, second_event, third_event]

    assert client.events.await_args_list == [
        call(changed_at=changed_at, cursor=None),
        call(changed_at=changed_at, cursor="abc"),
    ]


def test_paginator_empty():
    client = AsyncMock(spec=EventsProviderClient)
    client.events.return_value = {
        "results": [],
        "next": None,
    }

    changed_at = date(2000, 1, 1)

    async def collect_events():
        return [event async for event in EventsPaginator(client, changed_at)]

    result = asyncio.run(collect_events())

    assert result == []
    client.events.assert_awaited_once_with(
        changed_at=changed_at,
        cursor=None,
    )
