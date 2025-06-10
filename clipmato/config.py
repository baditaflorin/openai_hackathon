"""
Configuration constants for templates, static directory, and uploads.
"""
import os

# Base directory of the podcast_pipeline package
BASE_DIR = os.path.dirname(__file__)

# Jinja2Templates instance for rendering HTML templates
from fastapi.templating import Jinja2Templates
TEMPLATES = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Static files directory (CSS/JS/images)
STATIC_DIR = os.path.join(BASE_DIR, "static")