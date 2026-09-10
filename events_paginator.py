from collections.abc import AsyncIterator
from datetime import date
from urllib.parse import parse_qs, urlparse

from events_provider import EventsProviderClient


class EventsPaginator:
    def __init__(self, client: EventsProviderClient, changed_at: date):
        self.client = client
        self.changed_at = changed_at

    async def __aiter__(self) -> AsyncIterator[dict]:
        cursor = None
        seen_cursors: set[str] = set()

        while True:
            page = await self.client.events(
                changed_at=self.changed_at,
                cursor=cursor,
            )

            for event in page["results"]:
                yield event

            next_url = page["next"]
            if next_url is None:
                break

            params = parse_qs(urlparse(next_url).query)
            next_cursor = params.get("cursor", [None])[0]

            if next_cursor is None:
                raise ValueError("Next page URL has no cursor")

            if next_cursor in seen_cursors:
                raise ValueError("Pagination cursor repeated")

            seen_cursors.add(next_cursor)
            cursor = next_cursor
