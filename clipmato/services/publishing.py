"""Publish intent orchestration and background worker management."""
from __future__ import annotations

import asyncio
import copy
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from ..config import (
    PUBLISH_MAX_ATTEMPTS,
    PUBLISH_POLL_SECONDS,
    PUBLISH_RETRY_SECONDS,
    YOUTUBE_DEFAULT_PRIVACY_STATUS,
)
from ..governance.policy import PolicyDecision, evaluate_publish_action
from ..governance.storage import append_agent_evaluation
from ..prompts import record_publish_evaluations
from ..providers import (
    PublishAuthorizationError,
    PublishConfigurationError,
    PublishError,
    PublishPolicyError,
    PublishTemporaryError,
    YouTubePublisher,
)
from ..utils.metadata import get_metadata_record, mutate_metadata

logger = logging.getLogger(__name__)


class PublishingService:
    """Coordinates provider-specific publish jobs for records."""

    def __init__(self) -> None:
        self.youtube = YouTubePublisher()
        self._worker_task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None

    def get_provider_status(self, provider_key: str, redirect_uri: str | None = None) -> dict[str, Any]:
        if provider_key != self.youtube.key:
            raise ValueError(f"Unknown provider: {provider_key}")
        return self.youtube.get_connection_status(redirect_uri=redirect_uri)

    def schedule_record(
        self,
        record_id: str,
        schedule_time: str,
        publish_targets: list[str],
        youtube_privacy_status: str | None = None,
        override_actor: str | None = None,
        override_reason: str | None = None,
    ) -> dict[str, Any]:
        record = get_metadata_record(record_id)
        if record is None:
            raise KeyError(record_id)
        preview = copy.deepcopy(record)
        preview["schedule_time"] = schedule_time
        preview["publish_targets"] = list(publish_targets)
        if "YouTube" in publish_targets:
            self._enforce_publish_policy(
                preview,
                "youtube",
                action="schedule",
                override=self._policy_override(override_actor, override_reason),
            )
        now = datetime.now(UTC).isoformat()

        def _mutate(records: list[dict]) -> dict[str, Any]:
            for rec in records:
                if rec.get("id") != record_id:
                    continue

                rec["schedule_time"] = schedule_time
                rec["publish_targets"] = publish_targets
                publish_jobs = copy.deepcopy(rec.get("publish_jobs") or {})
                rec["publish_jobs"] = publish_jobs
                self._sync_youtube_job(
                    record=rec,
                    publish_jobs=publish_jobs,
                    schedule_time=schedule_time,
                    publish_targets=publish_targets,
                    youtube_privacy_status=youtube_privacy_status,
                    now_iso=now,
                )
                return copy.deepcopy(rec)
            raise KeyError(record_id)

        return mutate_metadata(_mutate)

    def queue_publish_now(
        self,
        record_id: str,
        *,
        override_actor: str | None = None,
        override_reason: str | None = None,
    ) -> dict[str, Any]:
        schedule_time = datetime.now().replace(second=0, microsecond=0).isoformat()
        record = get_metadata_record(record_id)
        if record is None:
            raise KeyError(record_id)
        publish_targets = list(record.get("publish_targets") or [])
        if "YouTube" not in publish_targets:
            publish_targets.append("YouTube")
        preview = copy.deepcopy(record)
        preview["schedule_time"] = schedule_time
        preview["publish_targets"] = publish_targets
        self._enforce_publish_policy(
            preview,
            "youtube",
            action="queue_now",
            override=self._policy_override(override_actor, override_reason),
        )
        youtube_job = (record.get("publish_jobs") or {}).get("youtube", {})
        return self.schedule_record(
            record_id=record_id,
            schedule_time=schedule_time,
            publish_targets=publish_targets,
            youtube_privacy_status=youtube_job.get("privacy_status"),
            override_actor=override_actor,
            override_reason=override_reason,
        )

    def retry_record(
        self,
        record_id: str,
        provider_key: str,
        *,
        override_actor: str | None = None,
        override_reason: str | None = None,
    ) -> dict[str, Any]:
        if provider_key != self.youtube.key:
            raise ValueError(f"Unknown provider: {provider_key}")
        record = get_metadata_record(record_id)
        if record is None:
            raise KeyError(record_id)
        self._enforce_publish_policy(
            record,
            provider_key,
            action="retry",
            override=self._policy_override(override_actor, override_reason),
        )

        now = datetime.now(UTC).isoformat()

        def _mutate(records: list[dict]) -> dict[str, Any]:
            for rec in records:
                if rec.get("id") != record_id:
                    continue
                publish_jobs = copy.deepcopy(rec.get("publish_jobs") or {})
                job = copy.deepcopy(publish_jobs.get(provider_key) or {})
                if not job:
                    raise KeyError(record_id)
                record_schedule = rec.get("schedule_time") or datetime.now().replace(second=0, microsecond=0).isoformat()
                rec["schedule_time"] = record_schedule
                targets = list(rec.get("publish_targets") or [])
                if "YouTube" not in targets:
                    targets.append("YouTube")
                rec["publish_targets"] = targets
                rec["publish_jobs"] = publish_jobs
                self._sync_youtube_job(
                    record=rec,
                    publish_jobs=publish_jobs,
                    schedule_time=record_schedule,
                    publish_targets=targets,
                    youtube_privacy_status=job.get("privacy_status"),
                    now_iso=now,
                    force_requeue=True,
                )
                publish_jobs[provider_key]["next_attempt_at"] = datetime.now().isoformat()
                return copy.deepcopy(rec)
            raise KeyError(record_id)

        return mutate_metadata(_mutate)

    def refresh_all_jobs(self) -> None:
        now = datetime.now(UTC).isoformat()

        def _mutate(records: list[dict]) -> None:
            for rec in records:
                publish_jobs = copy.deepcopy(rec.get("publish_jobs") or {})
                rec["publish_jobs"] = publish_jobs
                self._sync_youtube_job(
                    record=rec,
                    publish_jobs=publish_jobs,
                    schedule_time=rec.get("schedule_time"),
                    publish_targets=list(rec.get("publish_targets") or []),
                    youtube_privacy_status=(publish_jobs.get("youtube") or {}).get("privacy_status"),
                    now_iso=now,
                )

        mutate_metadata(_mutate)

    async def start_worker(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        self._stop_event = asyncio.Event()
        self._worker_task = asyncio.create_task(self._worker_loop(), name="clipmato-publisher")

    async def stop_worker(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self._worker_task = None

    async def publish_due_jobs_once(self) -> None:
        while True:
            claimed = self._claim_due_youtube_job()
            if claimed is None:
                return
            record = claimed["record"]
            job = claimed["job"]
            try:
                result = await asyncio.to_thread(self.youtube.publish, record, job)
            except PublishTemporaryError as exc:
                self._mark_failed(record["id"], "youtube", exc, retryable=True)
            except PublishAuthorizationError as exc:
                self._mark_blocked(record["id"], "youtube", str(exc), status="pending_connection")
            except PublishConfigurationError as exc:
                self._mark_blocked(record["id"], "youtube", str(exc), status="blocked")
            except PublishError as exc:
                self._mark_failed(record["id"], "youtube", exc, retryable=False)
            except Exception as exc:  # pragma: no cover - unexpected provider failures
                self._mark_failed(record["id"], "youtube", exc, retryable=True)
            else:
                self._mark_published(record["id"], "youtube", result.remote_id, result.remote_url, result.metadata)

    def _claim_due_youtube_job(self) -> dict[str, Any] | None:
        now = datetime.now()
        now_iso = datetime.now(UTC).isoformat()

        def _mutate(records: list[dict]) -> dict[str, Any] | None:
            for rec in records:
                job = (rec.get("publish_jobs") or {}).get("youtube")
                if not job:
                    continue
                if not job.get("enabled", True):
                    continue
                if job.get("status") != "scheduled":
                    continue
                due_at = job.get("next_attempt_at") or job.get("scheduled_for")
                if not due_at:
                    continue
                try:
                    due_dt = datetime.fromisoformat(due_at)
                except ValueError:
                    continue
                if due_dt > now:
                    continue
                job["status"] = "publishing"
                job["updated_at"] = now_iso
                job["last_attempt_at"] = now_iso
                job["attempt_count"] = int(job.get("attempt_count", 0)) + 1
                return {
                    "record": copy.deepcopy(rec),
                    "job": copy.deepcopy(job),
                }
            return None

        return mutate_metadata(_mutate)

    def _mark_published(
        self,
        record_id: str,
        provider_key: str,
        remote_id: str,
        remote_url: str,
        provider_metadata: dict[str, Any],
    ) -> None:
        now = datetime.now(UTC).isoformat()

        def _mutate(records: list[dict]) -> None:
            for rec in records:
                if rec.get("id") != record_id:
                    continue
                job = (rec.get("publish_jobs") or {}).get(provider_key)
                if not job:
                    return
                job["status"] = "published"
                job["published_at"] = now
                job["updated_at"] = now
                job["last_error"] = None
                job["next_attempt_at"] = None
                job["remote_id"] = remote_id
                job["remote_url"] = remote_url
                job["title"] = provider_metadata.get("title", job.get("title"))
                job["description"] = provider_metadata.get("description", job.get("description"))
                job["privacy_status"] = provider_metadata.get("privacy_status", job.get("privacy_status"))
                return

        mutate_metadata(_mutate)
        record_publish_evaluations(record_id, provider_key, remote_url)
        self._record_publish_job_evaluation(
            record_id,
            provider_key,
            status="published",
            metadata={
                "remote_id": remote_id,
                "remote_url": remote_url,
                "provider_metadata": copy.deepcopy(provider_metadata),
            },
        )

    def _mark_failed(self, record_id: str, provider_key: str, exc: Exception, retryable: bool) -> None:
        now = datetime.now(UTC)
        now_iso = now.isoformat()

        def _mutate(records: list[dict]) -> None:
            for rec in records:
                if rec.get("id") != record_id:
                    continue
                job = (rec.get("publish_jobs") or {}).get(provider_key)
                if not job:
                    return
                attempts = int(job.get("attempt_count", 0))
                job["updated_at"] = now_iso
                job["last_error"] = str(exc)
                if retryable and attempts < PUBLISH_MAX_ATTEMPTS:
                    job["status"] = "scheduled"
                    job["next_attempt_at"] = (now + timedelta(seconds=PUBLISH_RETRY_SECONDS)).isoformat()
                else:
                    job["status"] = "failed"
                    job["next_attempt_at"] = None
                return

        mutate_metadata(_mutate)
        self._record_publish_job_evaluation(
            record_id,
            provider_key,
            status="failed",
            metrics={"retryable": retryable},
            metadata={"error": str(exc)},
        )

    def _mark_blocked(self, record_id: str, provider_key: str, message: str, status: str) -> None:
        now = datetime.now(UTC).isoformat()

        def _mutate(records: list[dict]) -> None:
            for rec in records:
                if rec.get("id") != record_id:
                    continue
                job = (rec.get("publish_jobs") or {}).get(provider_key)
                if not job:
                    return
                job["status"] = status
                job["updated_at"] = now
                job["next_attempt_at"] = None
                job["last_error"] = message
                return

        mutate_metadata(_mutate)
        self._record_publish_job_evaluation(
            record_id,
            provider_key,
            status=status,
            metadata={"message": message},
        )

    async def _worker_loop(self) -> None:
        logger.info("Clipmato publishing worker started")
        try:
            if self._stop_event is None:
                return
            while not self._stop_event.is_set():
                try:
                    await self.publish_due_jobs_once()
                except Exception:
                    logger.exception("Publishing worker iteration failed")
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=PUBLISH_POLL_SECONDS)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.info("Clipmato publishing worker stopped")
            raise

    def _sync_youtube_job(
        self,
        record: dict[str, Any],
        publish_jobs: dict[str, Any],
        schedule_time: str | None,
        publish_targets: list[str],
        youtube_privacy_status: str | None,
        now_iso: str,
        force_requeue: bool = False,
    ) -> None:
        existing = copy.deepcopy(publish_jobs.get("youtube") or {})
        wants_youtube = "YouTube" in publish_targets

        if not wants_youtube:
            if not existing:
                return
            existing["enabled"] = False
            existing["updated_at"] = now_iso
            if existing.get("status") != "published":
                existing["status"] = "cancelled"
                existing["next_attempt_at"] = None
                existing["last_error"] = None
            publish_jobs["youtube"] = existing
            return

        title = (record.get("selected_title") or record.get("filename") or "Untitled episode").strip()
        description = (
            record.get("long_description")
            or record.get("short_description")
            or "Published by Clipmato."
        )
        privacy_status = (youtube_privacy_status or existing.get("privacy_status") or YOUTUBE_DEFAULT_PRIVACY_STATUS).strip().lower()
        if privacy_status not in {"private", "public", "unlisted"}:
            privacy_status = YOUTUBE_DEFAULT_PRIVACY_STATUS

        status = self.youtube.get_connection_status()
        if existing.get("status") == "published" and not force_requeue:
            job_status = "published"
            last_error = None
            next_attempt_at = None
        elif not schedule_time:
            job_status = "blocked"
            last_error = "Add a schedule time to activate YouTube publishing."
            next_attempt_at = None
        elif not status["available"]:
            job_status = "blocked"
            last_error = status["message"]
            next_attempt_at = None
        elif not status["connected"]:
            job_status = "pending_connection"
            last_error = "Connect YouTube to activate this scheduled publish."
            next_attempt_at = None
        else:
            job_status = "scheduled"
            last_error = None
            next_attempt_at = schedule_time

        publish_jobs["youtube"] = {
            "provider": "youtube",
            "display_name": "YouTube",
            "enabled": True,
            "status": job_status,
            "scheduled_for": schedule_time,
            "next_attempt_at": next_attempt_at,
            "created_at": existing.get("created_at") or now_iso,
            "updated_at": now_iso,
            "last_attempt_at": existing.get("last_attempt_at"),
            "published_at": existing.get("published_at") if job_status == "published" else None,
            "attempt_count": existing.get("attempt_count", 0) if job_status == "published" and not force_requeue else 0,
            "title": title,
            "description": description,
            "privacy_status": privacy_status,
            "remote_id": existing.get("remote_id") if job_status == "published" and not force_requeue else None,
            "remote_url": existing.get("remote_url") if job_status == "published" and not force_requeue else None,
            "last_error": last_error,
        }

    def _policy_override(self, actor: str | None, reason: str | None) -> dict[str, str] | None:
        if not actor or not reason:
            return None
        actor_name = str(actor).strip()
        reason_text = str(reason).strip()
        if not actor_name or not reason_text:
            return None
        return {
            "actor": actor_name,
            "reason": reason_text,
        }

    def _enforce_publish_policy(
        self,
        record: dict[str, Any],
        provider_key: str,
        *,
        action: str,
        override: dict[str, str] | None = None,
    ) -> None:
        decision = evaluate_publish_action(record, provider_key, action, override=override)
        self._record_publish_policy_evaluation(
            record_id=str(record.get("id") or ""),
            provider_key=provider_key,
            action=action,
            decision=decision,
            record=record,
        )
        if not decision.passed:
            raise PublishPolicyError(decision.summary_message())

    def _record_publish_policy_evaluation(
        self,
        *,
        record_id: str,
        provider_key: str,
        action: str,
        decision: PolicyDecision,
        record: dict[str, Any],
    ) -> None:
        append_agent_evaluation(
            {
                "evaluation_id": str(uuid4()),
                "subject_type": "publish_action",
                "subject_id": f"{record_id}:{provider_key}:{action}",
                "record_id": record_id,
                "action": action,
                "status": decision.status,
                "policy_status": decision.status,
                "metrics": {
                    "policy_passed": decision.passed,
                    "override_used": decision.override_used,
                },
                "metadata": {
                    "provider": provider_key,
                    "selected_title": record.get("selected_title"),
                    "schedule_time": record.get("schedule_time"),
                    "issues": [issue.as_dict() for issue in decision.issues],
                    "override_actor": decision.override_actor,
                    "override_reason": decision.override_reason,
                },
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    def _record_publish_job_evaluation(
        self,
        record_id: str,
        provider_key: str,
        *,
        status: str,
        metrics: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        append_agent_evaluation(
            {
                "evaluation_id": str(uuid4()),
                "subject_type": "publish_job",
                "subject_id": f"{record_id}:{provider_key}",
                "record_id": record_id,
                "action": "publish_result",
                "status": status,
                "metrics": copy.deepcopy(metrics or {}),
                "metadata": {
                    "provider": provider_key,
                    **copy.deepcopy(metadata or {}),
                },
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
