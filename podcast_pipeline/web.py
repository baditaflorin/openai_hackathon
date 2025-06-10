"""
Main FastAPI application entrypoint: mounts static files and includes routers.
"""
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from .routers.upload import router as upload_router
from .routers.record import router as record_router
from .routers.scheduler import router as scheduler_router

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include modularized routers for upload, record detail, and scheduler
app.include_router(upload_router)
app.include_router(record_router)
app.include_router(scheduler_router)