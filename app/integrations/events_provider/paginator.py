from collections.abc import AsyncIterator
from datetime import date
from urllib.parse import parse_qs, urlparse

from app.domain.ports import Provider
from app.domain.schemas import ProviderError


class EventsPaginator:
    def __init__(self, client: Provider, changed_at: date):
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

            if not isinstance(page.get("results"), list) or "next" not in page:
                raise ProviderError("Invalid pagination response from provider", 502)

            for event in page["results"]:
                yield event

            next_url = page["next"]
            if next_url is None:
                break
            if not isinstance(next_url, str):
                raise ProviderError("Invalid next page URL from provider", 502)

            params = parse_qs(urlparse(next_url).query)
            next_cursor = params.get("cursor", [None])[0]

            if next_cursor is None:
                raise ProviderError("Next page URL has no cursor", 502)

            if next_cursor in seen_cursors:
                raise ProviderError("Pagination cursor repeated", 502)

            seen_cursors.add(next_cursor)
            cursor = next_cursor
