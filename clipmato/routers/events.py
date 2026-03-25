"""Event-driven API routes for SSE consumption and webhook management."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..dependencies import get_eventing_service

router = APIRouter(prefix="/api/v1")


class WebhookCreateRequest(BaseModel):
    url: str
    secret: str | None = None
    event_types: list[str] = Field(default_factory=list)
    record_id: str | None = None
    run_id: str | None = None
    publish_job_id: str | None = None
    enabled: bool = True


class WebhookReplayRequest(BaseModel):
    from_event_id: str | None = None
    from_sequence: int | None = None


@router.get("/events")
async def list_events(
    after_sequence: int = Query(default=0, ge=0),
    record_id: str | None = None,
    run_id: str | None = None,
    publish_job_id: str | None = None,
    event_type: list[str] | None = Query(default=None, alias="type"),
    limit: int = Query(default=100, ge=1, le=1000),
    eventing_svc=Depends(get_eventing_service),
) -> JSONResponse:
    events = eventing_svc.list_events(
        after_sequence=after_sequence,
        record_id=record_id,
        run_id=run_id,
        publish_job_id=publish_job_id,
        event_types=event_type,
        limit=limit,
    )
    return JSONResponse({"events": events, "next_sequence": events[-1]["sequence"] if events else after_sequence})


@router.get("/events/stream")
async def stream_events(
    request: Request,
    after_sequence: int = Query(default=0, ge=0),
    record_id: str | None = None,
    run_id: str | None = None,
    publish_job_id: str | None = None,
    event_type: list[str] | None = Query(default=None, alias="type"),
    limit: int | None = Query(default=None, ge=1, le=1000),
    eventing_svc=Depends(get_eventing_service),
) -> StreamingResponse:
    async def iterator():
        emitted = 0
        async for event in eventing_svc.stream_events(
            after_sequence=after_sequence,
            record_id=record_id,
            run_id=run_id,
            publish_job_id=publish_job_id,
            event_types=event_type,
        ):
            if await request.is_disconnected():
                break
            yield (
                f"id: {event['sequence']}\n"
                f"event: {event['type']}\n"
                f"data: {json.dumps(event, separators=(',', ':'))}\n\n"
            )
            emitted += 1
            if limit is not None and emitted >= limit:
                break

    return StreamingResponse(iterator(), media_type="text/event-stream")


@router.get("/webhooks")
async def list_webhooks(eventing_svc=Depends(get_eventing_service)) -> JSONResponse:
    return JSONResponse({"webhooks": eventing_svc.list_webhooks()})


@router.post("/webhooks")
async def register_webhook(
    payload: WebhookCreateRequest,
    eventing_svc=Depends(get_eventing_service),
) -> JSONResponse:
    try:
        webhook = eventing_svc.register_webhook(
            url=payload.url,
            secret=payload.secret,
            event_types=payload.event_types,
            record_id=payload.record_id,
            run_id=payload.run_id,
            publish_job_id=payload.publish_job_id,
            enabled=payload.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(webhook, status_code=201)


@router.post("/webhooks/{webhook_id}/replay")
async def replay_webhook(
    webhook_id: str,
    payload: WebhookReplayRequest | None = None,
    eventing_svc=Depends(get_eventing_service),
) -> JSONResponse:
    try:
        replayed = eventing_svc.replay_webhook(
            webhook_id,
            from_event_id=(payload.from_event_id if payload else None),
            from_sequence=(payload.from_sequence if payload else None),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Webhook not found") from exc
    return JSONResponse(replayed)


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, eventing_svc=Depends(get_eventing_service)) -> JSONResponse:
    removed = eventing_svc.delete_webhook(webhook_id)
    if removed is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return JSONResponse(removed)
