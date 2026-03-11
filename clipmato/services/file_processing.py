from __future__ import annotations

import asyncio
import logging
from uuid import uuid4
from datetime import UTC, datetime

from ..steps.transcription import transcribe_audio
from ..steps.description_generation import generate_descriptions_with_prompt_async
from ..steps.entity_extraction import extract_entities_with_prompt_async
from ..steps.title_suggestion import propose_titles_with_prompt_async
from ..steps.script_generation import generate_script_with_prompt_async
from ..steps.audio_editing import edit_audio_async
from ..steps.distribution import distribute_with_prompt_async
from ..utils.progress import update_progress
from ..utils.metadata import append_metadata
from ..utils.project_context import normalize_project_context
from ..steps.silence_removal import remove_silence as remove_silence_step
from typing import Any
from ..orchestrator import Step, Pipeline

async def process_file_async(
    file_path: str,
    filename: str,
    record_id: str | None = None,
    remove_silence: bool = False,
    project_context: dict[str, Any] | None = None,
) -> dict:
    """
    Process an uploaded file through transcription, description & entity extraction,
    title suggestion, scripting, editing, and distribution. Returns a metadata record.
    If record_id is provided, it will be used; otherwise a new UUID is generated.
    Progress is emitted via the progress status file at each stage.
    """
    rec_id = record_id or str(uuid4())
    logger = logging.getLogger(__name__)
    logger.info(f"[{rec_id}] Starting processing file {file_path}, remove_silence={remove_silence}")

    context: dict[str, Any] = {
        "rec_id": rec_id,
        "file_path": file_path,
        "filename": filename,
        "project_context": normalize_project_context(project_context),
    }

    steps: list[Step] = [
        Step(
            "transcribing",
            transcribe_audio,
            input_keys=["file_path"],
            output_keys="transcript",
            to_thread=True,
            log_result=lambda r: f"{len(r)} characters",
        ),
        Step(
            "descriptions",
            generate_descriptions_with_prompt_async,
            input_keys=["transcript", "project_context", "rec_id"],
            output_keys=["desc", "desc_prompt_run"],
        ),
        Step(
            "entities",
            extract_entities_with_prompt_async,
            input_keys=["transcript", "rec_id"],
            output_keys=["entities", "entities_prompt_run"],
        ),
        Step(
            "titles",
            propose_titles_with_prompt_async,
            input_keys=["transcript", "project_context", "rec_id"],
            output_keys=["titles", "titles_prompt_run"],
        ),
        Step(
            "script",
            generate_script_with_prompt_async,
            input_keys=["transcript", "project_context", "rec_id"],
            output_keys=["script", "script_prompt_run"],
        ),
        Step(
            "editing",
            edit_audio_async,
            input_keys=["file_path"],
            output_keys="edited_audio",
            log_result=lambda p: f"output file: {p}",
        ),
    ]
    if remove_silence:
        steps.append(
            Step(
                "remove_silence",
                remove_silence_step,
                input_keys=["edited_audio"],
                output_keys=["original_duration", "trimmed_duration", "edited_audio"],
                to_thread=True,
                log_result=lambda res: f"original={res[0]:.2f}s trimmed={res[1]:.2f}s",
            )
        )
    steps.append(
        Step(
            "distribution",
            distribute_with_prompt_async,
            input_keys=["edited_audio", "project_context", "rec_id"],
            output_keys=["distribution", "distribution_prompt_run"],
        )
    )

    try:
        context = await Pipeline(steps).run(context)

        desc = context["desc"]
        entities = context["entities"]

        record: dict[str, Any] = {
            "id": rec_id,
            "filename": filename,
            "upload_time": datetime.now(UTC).isoformat(),
            "project_context": context["project_context"],
            "transcript": context["transcript"],
            "titles": context["titles"],
            "selected_title": None,
            "short_description": desc.get("short_description", ""),
            "long_description": desc.get("long_description", ""),
            "people": entities.get("people", []),
            "locations": entities.get("locations", []),
            "script": context["script"],
            "edited_audio": context["edited_audio"],
            "distribution": context["distribution"],
            "schedule_time": None,
            "publish_targets": [],
            "publish_jobs": {},
            "prompt_runs": {
                "title_suggestion": context["titles_prompt_run"],
                "description_generation": context["desc_prompt_run"],
                "entity_extraction": context["entities_prompt_run"],
                "script_generation": context["script_prompt_run"],
                "distribution_generation": context["distribution_prompt_run"],
            },
        }
        if remove_silence:
            record["original_duration"] = context["original_duration"]
            record["trimmed_duration"] = context["trimmed_duration"]

        append_metadata(record)
        update_progress(rec_id, "complete")
        return record
    except Exception as exc:
        logger.exception(f"[{rec_id}] Error during file processing")
        err_msg = str(exc)
        update_progress(rec_id, "error", err_msg)
        record = {
            "id": rec_id,
            "filename": filename,
            "upload_time": datetime.now(UTC).isoformat(),
            "project_context": context["project_context"],
            "error": err_msg,
            "schedule_time": None,
            "publish_targets": [],
            "publish_jobs": {},
            "prompt_runs": {},
        }
        append_metadata(record)
        return record
