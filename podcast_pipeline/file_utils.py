import shutil
from pathlib import Path
from fastapi import UploadFile

BASE_DIR = Path(__file__).parent
upload_dir = BASE_DIR / "uploads"
upload_dir.mkdir(exist_ok=True)

def save_upload_file(upload_file: UploadFile) -> str:
    """
    Save an uploaded FastAPI UploadFile to the uploads directory and return its file path.
    """
    dest = upload_dir / upload_file.filename
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return str(dest)