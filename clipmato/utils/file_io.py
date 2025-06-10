import shutil
from fastapi import UploadFile
from ..config import UPLOAD_DIR

# Directory where uploaded files are stored
upload_dir = UPLOAD_DIR
upload_dir.mkdir(parents=True, exist_ok=True)

def save_upload_file(upload_file: UploadFile) -> str:
    """
    Save an uploaded FastAPI UploadFile to the uploads directory
    and return its file path.
    """
    dest = upload_dir / upload_file.filename
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return str(dest)