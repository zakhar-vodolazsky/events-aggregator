import logging

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.domain.schemas import BusinessError


def register_error_handlers(app: FastAPI):
    @app.exception_handler(BusinessError)
    async def business_error(_request, exc):
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)

    @app.exception_handler(httpx.HTTPStatusError)
    async def provider_status_error(_request, exc):
        upstream = exc.response.status_code
        code = {400: 400, 404: 404, 429: 503}.get(upstream, 502)
        detail = {
            400: "Provider rejected the request; the seat may no longer be available",
            404: "Resource not found at provider",
            429: "Provider rate limit exceeded; try again later",
        }.get(upstream, "Events provider is unavailable")
        return JSONResponse({"detail": detail}, status_code=code)

    @app.exception_handler(httpx.RequestError)
    async def provider_network_error(_request, _exc):
        return JSONResponse(
            {"detail": "Provider connection failed; a submitted operation may have completed"},
            status_code=502,
        )

    @app.exception_handler(IntegrityError)
    async def conflict_error(_request, _exc):
        return JSONResponse({"detail": "Operation conflicts with existing data"}, status_code=409)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_request, exc):
        logging.getLogger(__name__).error("Database error: %s", type(exc).__name__)
        return JSONResponse({"detail": "Database operation failed"}, status_code=503)
