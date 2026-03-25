"""Main FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from . import __version__
from .api.errors import correlation_id_middleware, register_api_exception_handlers
from .config import STATIC_BUILD_DIR
from .dependencies import get_eventing_service, get_publishing_service
from .routers import list_routers
from .utils.metadata import metadata_cache
from .utils.static_assets import CachedStaticFiles, build_static_assets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop background services for the web app."""
    build_static_assets()
    metadata_cache.warm()
    eventing_service = get_eventing_service()
    publishing_service = get_publishing_service()
    await eventing_service.start_worker()
    await publishing_service.start_worker()
    try:
        yield
    finally:
        await publishing_service.stop_worker()
        await eventing_service.stop_worker()


app = FastAPI(
    title="Clipmato Public API",
    version=__version__,
    summary="Versioned public API contracts for uploads, progress, records, scheduling, and publishing.",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url=None,
)
app.middleware("http")(correlation_id_middleware)
register_api_exception_handlers(app)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.mount("/static", CachedStaticFiles(directory=STATIC_BUILD_DIR), name="static")

for router in list_routers():
    app.include_router(router)
