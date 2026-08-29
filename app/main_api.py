"""FastAPI application factory for Pushan V1.0."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from pathlib import Path
from time import perf_counter
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app import __version__
from app.config import settings
from app.database.db import DatabasePath, initialize_database
from app.logging_config import configure_logging, request_id_context


configure_logging()
logger = logging.getLogger(__name__)


def create_app(
    database_path: DatabasePath = settings.database_path,
    model_path: str | Path = settings.model_path,
    vector_store_path: str | Path = settings.vector_store_path,
) -> FastAPI:
    """Create a configurable API application for production or isolated tests."""

    @asynccontextmanager
    async def lifespan(api_app: FastAPI) -> AsyncIterator[None]:
        initialize_database(api_app.state.database_path)
        logger.info("Pushan API started")
        yield
        logger.info("Pushan API stopped")

    api_app = FastAPI(
        title="Pushan — The Next-Gen AI Agriculture Engine",
        version=__version__,
        description="Prototype AI-enabled irrigation process intelligence platform.",
        lifespan=lifespan,
    )
    api_app.state.database_path = database_path
    api_app.state.model_path = model_path
    api_app.state.vector_store_path = vector_store_path
    api_app.include_router(router)

    @api_app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"REQ-{uuid.uuid4().hex[:12].upper()}"
        token = request_id_context.set(request_id)
        started = perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = f"{(perf_counter() - started) * 1000:.2f}"
            logger.info("API request completed: %s %s %s", request.method, request.url.path, response.status_code)
            return response
        finally:
            request_id_context.reset(token)

    @api_app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        logger.exception("Unexpected API error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "Pushan could not complete the request.",
                "request_id": request_id_context.get(),
            },
        )

    return api_app


app = create_app()
