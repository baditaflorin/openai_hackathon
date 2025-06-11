# Clipmato

This repository contains a minimal prototype of Clipmato—an automated production pipeline built with the OpenAI Agents SDK.

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
python -m clipmato.pipeline
```
> **Note:** We include `simpleaudio` in `requirements.txt` to satisfy pydub’s audio-operation needs.
> Also ensure your Python build provides the standard `audioop` extension (or install a `pyaudioop` fallback) so that pydub silence removal will work without errors.

### Modular API

You can also import and run individual pipeline steps (including transcription and title suggestions):
```python
from clipmato.steps import (
    transcribe_audio,
    propose_titles,
    curate_content,
    generate_script,
    edit_audio,
    distribute,
)

# Transcribe a raw audio file to text

# Transcribe a raw audio file to text
transcript = transcribe_audio("path/to/raw_audio.mp3")

# Get 5 title suggestions from the transcript
titles = propose_titles(transcript)
# titles is a list of strings

# Curate content, generate script, edit audio, and distribute
topic = curate_content("Find a trending tech topic")
script = generate_script(topic)
edited_audio = edit_audio("path/to/raw_audio.mp3")
distribution = distribute(edited_audio)
```

Or run the full pipeline programmatically:
```python
from clipmato.pipeline import run_pipeline

outputs = run_pipeline()
```

You can also access the scheduling utilities directly:

```python
from clipmato.services.scheduling import generate_dummy_schedule, propose_schedule_async
from clipmato.utils.metadata import read_metadata

records = read_metadata()
# Synchronous dummy schedule (one episode per day)
dummy_schedule = generate_dummy_schedule(records)

import asyncio
# Asynchronously propose schedule via the Scheduler Agent (fallback to dummy on error)
schedules = asyncio.run(propose_schedule_async(records))
```

### Plugin Infrastructure

Clipmato supports a plugin mechanism for both agents and pipeline steps.
Simply drop a new Python module into the `clipmato/agents` or `clipmato/steps`
directory, and Clipmato will automatically discover and load your plugin.

#### Agents

To define a new agent, create a file in `clipmato/agents` and define an
`Agent` instance with a variable name ending in `_agent`. For example:

```python
# clipmato/agents/my_custom_agent.py
from agents import Agent

my_custom_agent = Agent(
    name="My Custom Agent",
    instructions="""
    Your instructions here...
    """
)
```

Clipmato will register `my_custom_agent`, and you can retrieve it at runtime:

```python
from clipmato.agents import list_agents, get_agent

agents = list_agents()
agent = get_agent("My Custom Agent")
```

#### Steps

To define a new pipeline step, create a file in `clipmato/steps` and define
callable functions. For example:

```python
# clipmato/steps/my_step.py

def my_step(input_data: str) -> str:
    # perform processing...
    return result
```

Your step function will be available through the `clipmato.steps` namespace:

```python
from clipmato.steps import my_step
```

#### Routers

To define a new set of web endpoints, create a file in `clipmato/routers`
and define an `APIRouter` instance named `router`. Clipmato will auto-discover
your router and include it in the FastAPI app. For example:

```python
# clipmato/routers/my_feature.py
from fastapi import APIRouter

router = APIRouter(prefix="/my_feature")

@router.get("/")
async def read_my_feature():
    return {"message": "Hello from my feature"}
```

### GUI

You can also launch a very small Tkinter interface (requires installed Tcl/Tk support):

```bash
python -m clipmato.gui
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

You can also run a FastAPI-based web interface for drag-and-drop file upload and processing. The home page (Episode Dashboard) displays all your episodes as responsive cards—click any card to view its detailed transcript, short & long descriptions, and extracted entities.

```bash
pip install -r requirements.txt
uvicorn clipmato.web:app --reload
```

Then visit `http://127.0.0.1:8000/` in your browser.

- You can drag-and-drop or select a **video or audio file** in the web UI to upload.
- An inline per-episode progress bar on each card displays upload and processing stages, allowing multiple concurrent uploads without blocking the UI.
- If an error occurs during processing, the progress badge on the card will turn red and display the error message.
- Episodes appear in the Episode Dashboard as a responsive grid of cards below the upload zone; click any card to view its details.
- If your audio file exceeds OpenAI Whisper's 25MB upload limit, it will be automatically split into smaller segments and transcribed sequentially, then combined into a single transcript.
- On the episode detail page, you'll see 5 suggested titles—choose one as your favorite and save it for later use.
- Each record’s detail page now shows a **short description** and a **long description** generated from the transcript, along with any referenced **people** and **locations** automatically extracted.
- You can record your screen, your webcam, or both directly in the web UI; once you finish recording, it’s automatically uploaded and processed.
- A **Remove silence** checkbox in the upload controls allows you to automatically trim long silent sections from your recordings. The episode detail page will display both the original and trimmed durations when enabled.
- You can also delete old records (and their audio files) directly from the home page using the "Delete" button next to each processed file.

### Scheduler

A scheduling page is available at `/scheduler` to manually or automatically assign posting dates to your processed episodes:

- Click the **Scheduler** button on the home page (or visit `/scheduler`) to view all episodes with their chosen title.
- A publication calendar at the top displays all scheduled release dates for the current month.
- Use **Auto-Schedule All** to automatically propose posting dates based on your selected cadence (daily, weekly, or every N days). Make sure you've chosen a title for each unscheduled episode first.
- Manually set each episode’s date/time and select **publish destinations** (YouTube, Spotify, Apple Podcasts) using the form controls, then click **Save**. You cannot schedule an episode until a title has been selected.

- A loading spinner overlay will appear while scheduling operations are in progress, so you know when the page is working.
