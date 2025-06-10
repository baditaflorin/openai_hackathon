from uuid import uuid4
from datetime import datetime

from ..steps.transcription import transcribe_audio
from ..steps.title_suggestion import propose_titles_async
from ..steps.script_generation import generate_script_async
from ..steps.audio_editing import edit_audio_async
from ..steps.distribution import distribute_async

async def process_file_async(file_path: str, filename: str) -> dict:
    """
    Process an uploaded file through transcription, title suggestion, scripting,
    editing, and distribution. Returns a metadata record dictionary.
    """
    transcript = transcribe_audio(file_path)
    titles = await propose_titles_async(transcript)
    script = await generate_script_async(transcript)
    edited_audio = await edit_audio_async(file_path)
    distribution = await distribute_async(edited_audio)

    return {
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