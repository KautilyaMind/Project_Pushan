"""FastAPI application entry point for Pushan V0.8."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.database.db import DEFAULT_DATABASE_PATH, DatabasePath, initialize_database
from app.ml.train import DEFAULT_MODEL_PATH
from app.rag.vector_store import DEFAULT_VECTOR_STORE_PATH


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(
    database_path: DatabasePath = DEFAULT_DATABASE_PATH,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    vector_store_path: str | Path = DEFAULT_VECTOR_STORE_PATH,
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
        version="0.8",
        description="Prototype AI-enabled irrigation process intelligence platform.",
        lifespan=lifespan,
    )
    api_app.state.database_path = database_path
    api_app.state.model_path = model_path
    api_app.state.vector_store_path = vector_store_path
    api_app.include_router(router)

    @api_app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        logger.exception("Unexpected API error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected internal error occurred."},
        )

    return api_app


app = create_app()
