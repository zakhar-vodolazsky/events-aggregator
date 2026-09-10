import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.core.config import get_settings
from app.core.container import Container


def create_app(container: Container | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(running_app: FastAPI):
        logging.basicConfig(level=logging.INFO)
        running_app.state.container = (
            container if container is not None else Container(get_settings())
        )
        async with running_app.state.container.lifespan():
            yield

    application = FastAPI(title="Events Aggregator", lifespan=lifespan)
    register_error_handlers(application)
    application.include_router(router)
    return application


app = create_app()
