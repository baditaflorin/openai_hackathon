import asyncio
from uuid import uuid4
from datetime import datetime

from ..steps.transcription import transcribe_audio
from ..steps.description_generation import generate_descriptions_async
from ..steps.entity_extraction import extract_entities_async
from ..steps.title_suggestion import propose_titles_async
from ..steps.script_generation import generate_script_async
from ..steps.audio_editing import edit_audio_async
from ..steps.distribution import distribute_async
from ..utils.progress import update_progress
from ..utils.metadata import append_metadata

async def process_file_async(
    file_path: str,
    filename: str,
    record_id: str | None = None,
) -> dict:
    """
    Process an uploaded file through transcription, description & entity extraction,
    title suggestion, scripting, editing, and distribution. Returns a metadata record.
    If record_id is provided, it will be used; otherwise a new UUID is generated.
    Progress is emitted via the progress status file at each stage.
    """
    # determine or generate the record ID for status tracking
    rec_id = record_id or str(uuid4())

    # transcription stage
    update_progress(rec_id, "transcribing")
    transcript = await asyncio.to_thread(transcribe_audio, file_path)

    # description and entity extraction stage
    update_progress(rec_id, "descriptions")
    desc = await generate_descriptions_async(transcript)
    update_progress(rec_id, "entities")
    entities = await extract_entities_async(transcript)

    # title suggestion and script generation stage
    update_progress(rec_id, "titles")
    titles = await propose_titles_async(transcript)
    update_progress(rec_id, "script")
    script = await generate_script_async(transcript)

    # audio editing and distribution stage
    update_progress(rec_id, "editing")
    edited_audio = await edit_audio_async(file_path)
    update_progress(rec_id, "distribution")
    distribution = await distribute_async(edited_audio)

    # finalize and save metadata
    record = {
        "id": rec_id,
        "filename": filename,
        "upload_time": datetime.utcnow().isoformat(),
        "transcript": transcript,
        "titles": titles,
        "selected_title": None,
        "short_description": desc.get("short_description", ""),
        "long_description": desc.get("long_description", ""),
        "people": entities.get("people", []),
        "locations": entities.get("locations", []),
        "script": script,
        "edited_audio": edited_audio,
        "distribution": distribution,
    }
    append_metadata(record)

    # complete
    update_progress(rec_id, "complete")
    return record
