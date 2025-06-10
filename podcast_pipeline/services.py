from uuid import uuid4
from datetime import datetime

from .steps import (
    transcribe_audio,
    propose_titles_async,
    generate_script_async,
    edit_audio_async,
    distribute_async,
)

async def process_file_async(file_path: str, filename: str) -> dict:
    """
    Process an uploaded file through transcription, scripting, editing, and distribution.
    Returns a metadata record dictionary.
    """
    transcript = transcribe_audio(file_path)
    titles = await propose_titles_async(transcript)
    script = await generate_script_async(transcript)
    edited_audio = await edit_audio_async(file_path)
    distribution = await distribute_async(edited_audio)

    record = {
        "id": str(uuid4()),
        "filename": filename,
        "upload_time": datetime.utcnow().isoformat(),
        "transcript": transcript,
        "titles": titles,
        "selected_title": None,
        "script": script,
        "edited_audio": edited_audio,
        "distribution": distribution,
    }
    return record