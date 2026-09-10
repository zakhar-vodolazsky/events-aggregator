from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Place
from app.domain.schemas import PlaceData


class PlaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, place: PlaceData) -> None:
        values = place.model_dump()
        statement = insert(Place).values(**values)
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[Place.id],
                set_={key: getattr(statement.excluded, key) for key in values if key != "id"},
                where=or_(
                    Place.changed_at.is_(None), Place.changed_at < statement.excluded.changed_at
                ),
            )
        )

    async def get(self, place_id: UUID) -> Place | None:
        result = await self.session.get(Place, place_id)
        return cast(Place | None, result)

    async def save(
        self,
        *,
        place_id: UUID,
        name: str,
        city: str | None,
        address: str | None,
        seats_pattern: str | None,
        created_at: datetime,
        changed_at: datetime,
    ) -> Place:
        place = await self.get(place_id)

        if place is None:
            place = Place(id=place_id)
            self.session.add(place)

        place.name = name
        place.city = city
        place.address = address
        place.seats_pattern = seats_pattern
        place.created_at = created_at
        place.changed_at = changed_at

        await self.session.flush()
        return place
