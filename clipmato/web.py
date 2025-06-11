"""
Main FastAPI application entrypoint: mounts static files and includes routers.
"""
import os
import logging

logging.basicConfig(level=logging.INFO)
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from .routers import list_routers

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

for router in list_routers():
    app.include_router(router)