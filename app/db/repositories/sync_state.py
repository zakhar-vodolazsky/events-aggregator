from datetime import datetime
from typing import cast

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SyncState
from app.domain.schemas import SyncData


class SyncStateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self) -> SyncState:
        await self.session.execute(
            insert(SyncState).values(id=1, sync_status="pending").on_conflict_do_nothing()
        )
        state = cast(
            SyncState | None,
            await self.session.get(SyncState, 1),
        )

        if state is None:
            state = SyncState(id=1, sync_status="pending")
            self.session.add(state)
            await self.session.flush()

        return state

    async def read(self) -> SyncData:
        return SyncData.model_validate(await self.get_or_create())

    async def update(
        self,
        status: str,
        *,
        changed_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        state = await self.get_or_create()
        state.sync_status = status
        if completed_at is not None:
            state.last_sync_time = completed_at
            state.last_changed_at = changed_at
        await self.session.flush()
