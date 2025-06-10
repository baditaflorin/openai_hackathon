"""
Common imports for router modules: templates, metadata, progress,
file I/O, and services.
"""
from ..config import TEMPLATES
from ..utils.metadata import read_metadata, update_metadata, remove_metadata
from ..utils.progress import update_progress, read_progress, enrich_with_progress
from ..utils.file_io import save_upload_file, upload_dir
from ..services.file_processing import process_file_async
from ..services.scheduling import propose_schedule_async

__all__ = [
    "TEMPLATES",
    "read_metadata",
    "update_metadata",
    "remove_metadata",
    "update_progress",
    "read_progress",
    "enrich_with_progress",
    "save_upload_file",
    "upload_dir",
    "process_file_async",
    "propose_schedule_async",
]