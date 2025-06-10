import os

from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .steps import transcribe_audio, generate_script_async, edit_audio_async, distribute_async
from .file_utils import save_upload_file
from .web_utils import read_metadata, append_metadata
from .services import process_file_async


app = FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(upload_dir, exist_ok=True)
metadata_path = os.path.join(upload_dir, "metadata.json")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the upload form and list of processed files."""
    records = read_metadata()
    return templates.TemplateResponse(
        "index.html", {"request": request, "records": records}
    )

@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...)):
    """Handle uploaded audio file and run through the pipeline."""
    file_path = save_upload_file(file)
    record = await process_file_async(file_path, file.filename)
    append_metadata(record)

    return templates.TemplateResponse(
        "result.html",
        {"request": request, **record},
    )


@app.get("/record/{record_id}", response_class=HTMLResponse)
async def record_detail(request: Request, record_id: str):
    """Show detailed view for a processed record."""
    records = read_metadata()
    record = next((it for it in records if it["id"] == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return templates.TemplateResponse(
        "record.html", {"request": request, "record": record}
    )