"""JSON routes for inspecting persisted agent runs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..dependencies import get_agent_run_service


router = APIRouter()


@router.get("/agent-runs/{run_id}")
async def agent_run_detail(
    run_id: str,
    agent_runs=Depends(get_agent_run_service),
) -> JSONResponse:
    """Return a persisted agent run trace as JSON."""
    run = agent_runs.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return JSONResponse(run)
