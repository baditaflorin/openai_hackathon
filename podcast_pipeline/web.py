import os
import shutil

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .steps import (
    transcribe_audio,
    generate_script_async,
    edit_audio_async,
    distribute_async,
)


app = FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(upload_dir, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the upload form."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, file: UploadFile = File(...)):
    """Handle uploaded audio file and run through the pipeline."""
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    transcript = transcribe_audio(file_path)

    script = await generate_script_async(transcript)

    edited_audio = await edit_audio_async(file_path)

    distribution = await distribute_async(edited_audio)

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "filename": file.filename,
            "transcript": transcript,
            "script": script,
            "distribution": distribution,
        },
    )