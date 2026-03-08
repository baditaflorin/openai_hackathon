"""Main FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from .dependencies import get_publishing_service
from .routers import list_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop background services for the web app."""
    publishing_service = get_publishing_service()
    await publishing_service.start_worker()
    try:
        yield
    finally:
        await publishing_service.stop_worker()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

for router in list_routers():
    app.include_router(router)
