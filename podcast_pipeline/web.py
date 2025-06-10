import os

from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .steps import transcribe_audio
from .file_utils import save_upload_file
from .web_utils import read_metadata, append_metadata, update_metadata, remove_metadata
from .services import process_file_async


app = FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

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


@app.post("/record/{record_id}/title", response_class=HTMLResponse)
async def select_title(request: Request, record_id: str, selected_title: str = Form(...)):
    """
    Handle the user selection of a title for a processed record.
    """
    records = read_metadata()
    record = next((it for it in records if it["id"] == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    update_metadata(record_id, {"selected_title": selected_title})
    return RedirectResponse(url=f"/record/{record_id}", status_code=303)


@app.post("/record/{record_id}/delete")
async def delete_record(record_id: str):
    """Delete a processed record and its associated files."""
    rec = remove_metadata(record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    from .file_utils import upload_dir
    from pathlib import Path

    src = upload_dir / rec.get("filename", "")
    if src.exists():
        try:
            src.unlink()
        except Exception:
            pass
    dst = Path(src).with_suffix('.wav')
    if dst.exists():
        try:
            dst.unlink()
        except Exception:
            pass
    return RedirectResponse(url="/", status_code=303)