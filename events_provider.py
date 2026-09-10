from datetime import date
from uuid import UUID

import httpx


# HTTP-client class for external APIs
class EventsProviderClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def events(
        self,
        changed_at: date,
        cursor: str | None = None,
    ) -> dict:
        params = {"changed_at": changed_at.isoformat()}
        if cursor is not None:
            params["cursor"] = cursor

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/events/",
                headers={"x-api-key": self.api_key},
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def seats(self, event_id: UUID) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/events/{event_id}/seats/",
                headers={"x-api-key": self.api_key},
            )
            response.raise_for_status()
            return response.json()

    async def register(
        self,
        event_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/events/{event_id}/register/",
                headers={"x-api-key": self.api_key},
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "seat": seat,
                },
            )
            response.raise_for_status()
            return response.json()

    async def unregister(self, event_id: UUID, ticket_id: UUID) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                "DELETE",
                f"{self.base_url}/api/events/{event_id}/unregister/",
                headers={"x-api-key": self.api_key},
                json={"ticket_id": str(ticket_id)},
            )
            response.raise_for_status()
            return response.json()
