from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def create_engine(database_url):
    return create_async_engine(database_url, pool_pre_ping=True, hide_parameters=True)


def create_session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)
