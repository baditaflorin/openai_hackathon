"""
Dependency providers for Clipmato Web/API layer: templates, file I/O,
metadata, progress tracking, file processing, and scheduling services.
"""
import logging

from fastapi.templating import Jinja2Templates

from .config import TEMPLATES, UPLOAD_DIR
from .utils.file_io import save_upload_file
from .utils.metadata import read_metadata, update_metadata, remove_metadata
from .utils.progress import update_progress, read_progress, enrich_with_progress
from .services.file_processing import process_file_async
from .services.scheduling import propose_schedule_async

logger = logging.getLogger(__name__)


class FileIOService:
    """Service for handling file uploads."""

    def __init__(self):
        self.upload_dir = UPLOAD_DIR

    def save(self, upload_file):
        return save_upload_file(upload_file)


class MetadataService:
    """Service for reading, updating, and removing metadata records."""

    def read(self):
        return read_metadata()

    def update(self, record_id: str, data: dict):
        return update_metadata(record_id, data)

    def remove(self, record_id: str):
        return remove_metadata(record_id)


class ProgressService:
    """Service for tracking and reading pipeline progress."""

    def update(self, record_id: str, stage: str, message: str | None = None):
        return update_progress(record_id, stage, message)

    def read(self, record_id: str):
        return read_progress(record_id)

    def enrich(self, records: list[dict]):
        return enrich_with_progress(records)


class ProcessingService:
    """Service for asynchronous file processing pipeline."""

    async def process(self, *args, **kwargs):
        return await process_file_async(*args, **kwargs)


class SchedulingService:
    """Service for proposing and applying schedules."""

    async def propose(self, *args, **kwargs):
        return await propose_schedule_async(*args, **kwargs)


def get_templates() -> Jinja2Templates:
    """Dependency: Jinja2 templates instance."""
    return TEMPLATES


def get_file_io_service() -> FileIOService:
    """Dependency: File IO service instance."""
    return FileIOService()


def get_metadata_service() -> MetadataService:
    """Dependency: Metadata service instance."""
    return MetadataService()


def get_progress_service() -> ProgressService:
    """Dependency: Progress tracking service instance."""
    return ProgressService()


def get_processing_service() -> ProcessingService:
    """Dependency: Processing service instance."""
    return ProcessingService()


def get_scheduling_service() -> SchedulingService:
    """Dependency: Scheduling service instance."""
    return SchedulingService()