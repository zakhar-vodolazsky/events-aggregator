import asyncio
from datetime import date
from uuid import UUID

import httpx

from app.domain.schemas import ProviderError


# HTTP-client class for external APIs
class EventsProviderClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def _send(self, method: str, path: str, **kwargs) -> dict:
        # Retry reads only. Retrying a registration after a timeout can sell a seat twice.
        attempts = 3 if method == "GET" else 1
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(attempts):
                try:
                    url = f"{self.base_url}{path}"
                    headers = {"x-api-key": self.api_key}
                    if method == "GET":
                        response = await client.get(url, headers=headers, **kwargs)
                    elif method == "POST":
                        response = await client.post(url, headers=headers, **kwargs)
                    else:
                        response = await client.request(method, url, headers=headers, **kwargs)
                    if response.status_code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                        await asyncio.sleep(0.25 * 2**attempt)
                        continue
                    response.raise_for_status()
                    try:
                        result = response.json()
                    except ValueError as exc:
                        raise ProviderError("Provider returned invalid JSON", 502) from exc
                    if not isinstance(result, dict):
                        raise ProviderError("Provider returned an invalid response", 502)
                    return result
                except httpx.RequestError:
                    if attempt == attempts - 1:
                        raise
                    await asyncio.sleep(0.25 * 2**attempt)
        raise ProviderError("Provider request failed", 502)

    async def events(
        self,
        changed_at: date,
        cursor: str | None = None,
    ) -> dict:
        params = {"changed_at": changed_at.isoformat()}
        if cursor is not None:
            params["cursor"] = cursor

        return await self._send("GET", "/api/events/", params=params)

    async def seats(self, event_id: UUID) -> dict:
        return await self._send("GET", f"/api/events/{event_id}/seats/")

    async def register(
        self,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> dict:
        return await self._send(
            "POST",
            f"/api/events/{event_id}/register/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "seat": seat,
            },
        )

    async def unregister(self, event_id: UUID, ticket_id: UUID) -> dict:
        return await self._send(
            "DELETE",
            f"/api/events/{event_id}/unregister/",
            json={"ticket_id": str(ticket_id)},
        )
