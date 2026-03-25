"""Main FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api_support import (
    CorrelationIdMiddleware,
    api_http_exception_handler,
    api_unhandled_exception_handler,
    api_validation_exception_handler,
)
from .config import STATIC_BUILD_DIR
from .dependencies import get_publishing_service
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
    publishing_service = get_publishing_service()
    await publishing_service.start_worker()
    try:
        yield
    finally:
        await publishing_service.stop_worker()


app = FastAPI(lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.mount("/static", CachedStaticFiles(directory=STATIC_BUILD_DIR), name="static")
app.add_exception_handler(StarletteHTTPException, api_http_exception_handler)
app.add_exception_handler(RequestValidationError, api_validation_exception_handler)
app.add_exception_handler(Exception, api_unhandled_exception_handler)

for router in list_routers():
    app.include_router(router)
