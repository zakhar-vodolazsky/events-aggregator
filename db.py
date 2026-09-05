from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import get_settings

engine = create_async_engine(
    url=get_settings().database_url,
    pool_pre_ping=True,
    hide_parameters=True,
    pool_size=10,
    max_overflow=10,
)

SessionFactory = async_sessionmaker(bind=engine, expire_on_commit=False)


@lru_cache
async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
