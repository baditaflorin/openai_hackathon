# Automated Podcast Production Pipeline

This repository contains a minimal prototype of a podcast production pipeline built with the OpenAI Agents SDK.

## Components
- **Content Curator Agent** – Suggests topics and guests.
- **Script Writer Agent** – Generates show notes and interview questions.
- **Audio Editor Agent** – Placeholder for audio processing logic.
- **Distributor Agent** – Publishes episodes.

## Usage
Install dependencies and run the example pipeline:
```bash
pip install -r requirements.txt
python -m podcast_pipeline.pipeline
```

### Modular API

You can also import and run individual pipeline steps:
```python
from podcast_pipeline.steps import (
    curate_content,
    generate_script,
    edit_audio,
    distribute,
)

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
