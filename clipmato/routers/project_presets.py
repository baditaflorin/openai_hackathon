"""Routes for saving and deleting reusable project presets."""
from __future__ import annotations

from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from ..dependencies import get_project_preset_service

router = APIRouter()


def _redirect(kind: str, message: str) -> RedirectResponse:
    return RedirectResponse(url=f"/?preset_{kind}={quote_plus(message)}#capture", status_code=303)


@router.post("/project-presets/save")
async def save_project_preset(
    request: Request,
    project_preset_svc=Depends(get_project_preset_service),
) -> RedirectResponse:
    """Persist a project preset from the capture workspace."""
    form = await request.form()
    try:
        project_preset_svc.save(
            {
                "preset_id": form.get("preset_id"),
                "label": form.get("preset_label"),
                "project_name": form.get("project_name"),
                "project_summary": form.get("project_summary"),
                "project_topics": form.get("project_topics"),
                "project_prompt_prefix": form.get("project_prompt_prefix"),
                "project_prompt_suffix": form.get("project_prompt_suffix"),
            }
        )
    except ValueError as exc:
        return _redirect("error", str(exc))
    return _redirect("notice", "Project preset saved.")


@router.post("/project-presets/{preset_id}/delete")
async def delete_project_preset(
    preset_id: str,
    project_preset_svc=Depends(get_project_preset_service),
) -> RedirectResponse:
    """Delete one saved project preset."""
    project_preset_svc.delete(preset_id)
    return _redirect("notice", "Project preset removed.")
