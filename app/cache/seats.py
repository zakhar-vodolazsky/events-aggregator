import asyncio
from collections import OrderedDict
from time import monotonic
from uuid import UUID

from app.domain.ports import Provider
from app.domain.schemas import ProviderError


class SeatsCache:
    def __init__(self, ttl: float = 30, max_entries: int = 256):
        self.ttl = ttl
        self.max_entries = max_entries
        self.values: OrderedDict[UUID, tuple[float, tuple[str, ...]]] = OrderedDict()
        self.generation = 0
        # Fixed lock pool avoids leaking a lock for every requested event ID.
        self.locks = [asyncio.Lock() for _ in range(64)]

    def invalidate(self, event_id: UUID) -> None:
        self.generation += 1
        self.values.pop(event_id, None)

    def clear(self) -> None:
        self.generation += 1
        self.values.clear()

    async def get(self, event_id: UUID, provider: Provider, *, fresh: bool = False) -> list[str]:
        async with self.locks[hash(event_id) % len(self.locks)]:
            cached = self.values.get(event_id)
            if not fresh and cached and cached[0] > monotonic():
                self.values.move_to_end(event_id)
                return list(cached[1])
            generation = self.generation
            result = await provider.seats(event_id)
            seats = result.get("seats")
            if not isinstance(seats, list) or not all(isinstance(s, str) for s in seats):
                raise ProviderError("Invalid seats response from provider", 502)
            # Fresh booking checks are not cached: a booking will immediately invalidate them.
            if not fresh and generation == self.generation:
                self.values[event_id] = (monotonic() + self.ttl, tuple(seats))
                self.values.move_to_end(event_id)
                while len(self.values) > self.max_entries:
                    self.values.popitem(last=False)
            return seats
