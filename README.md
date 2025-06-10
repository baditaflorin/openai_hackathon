# Automated Podcast Production Pipeline

This repository contains a minimal prototype of a podcast production pipeline built with the OpenAI Agents SDK.

## Components
- **Content Curator Agent** – Suggests topics and guests.
- **Script Writer Agent** – Generates show notes and interview questions.
- **Audio Editor Agent** – Placeholder for audio processing logic.
- **Distributor Agent** – Publishes episodes.

## Usage
### Authentication

Make sure you have your OpenAI API key set in your environment:

```bash
export OPENAI_API_KEY="your_openai_api_key_here"
```

### Prerequisites

Ensure you have `ffmpeg` installed and available on your PATH so uploaded audio can be converted into a Whisper-supported format:

```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

Install dependencies and run the example pipeline:
```bash
pip install -r requirements.txt
python -m podcast_pipeline.pipeline
```

### Modular API

You can also import and run individual pipeline steps (including transcription):
```python
from podcast_pipeline.steps import (
    transcribe_audio,
    curate_content,
    generate_script,
    edit_audio,
    distribute,
)

# Transcribe a raw audio file to text
transcript = transcribe_audio("path/to/raw_audio.mp3")

# Curate content, generate script, edit audio, and distribute
topic = curate_content("Find a trending tech topic")
script = generate_script(topic)
edited_audio = edit_audio("path/to/raw_audio.mp3")
distribution = distribute(edited_audio)
```

Or run the full pipeline programmatically:
```python
from podcast_pipeline.pipeline import run_pipeline

outputs = run_pipeline()
```

### GUI

You can also launch a very small Tkinter interface (requires installed Tcl/Tk support):

```bash
python -m podcast_pipeline.gui
```

> **macOS**: If you get `ModuleNotFoundError: No module named '_tkinter'`, install Tcl/Tk and reinstall Python from python.org or via Homebrew:
> ```bash
> brew install tcl-tk
> brew reinstall python --with-tcl-tk
> ```
>
> **Ubuntu/Debian**:
> ```bash
> sudo apt-get install python3-tk
> ```
>
> **Windows**: Make sure you installed Python from python.org, which includes Tcl/Tk by default.

### Web Application

You can also run a FastAPI-based web interface for drag-and-drop file upload and processing. The home page now lists all previously processed files—click any file to view its detailed transcript, script, and distribution.

```bash
pip install -r requirements.txt
uvicorn podcast_pipeline.web:app --reload
```

Then visit `http://127.0.0.1:8000/` in your browser.

You can either drag-and-drop your audio file or click the "Or select file" button in the web UI to upload.

- A loading spinner overlay will appear while your file is being uploaded and processed, giving you visual feedback.
- Processed files will appear in a list below the upload zone; click a filename to view its details.
