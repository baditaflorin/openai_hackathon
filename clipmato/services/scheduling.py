"""
Utilities for schedule suggestion: dummy implementation and Agent-based.
"""
import json
import logging
from datetime import datetime, timedelta

from agents import Runner
from ..agents.scheduler_agent import scheduler_agent
from .service_utils import with_fallback
from ..config import DEFAULT_CADENCE, CADENCE_INTERVALS, DEFAULT_PUBLISH_HOUR

logger = logging.getLogger(__name__)

def generate_dummy_schedule(
    records: list[dict], cadence: str = DEFAULT_CADENCE, n_days: int | None = None
) -> dict[str, str]:
    """
    Generate a simple dummy schedule based on cadence:
    - 'daily': one per day starting tomorrow at 09:00 UTC
    - 'weekly': one per week starting one week from today at 09:00 UTC
    - 'every_n': one every n_days starting n_days from today at 09:00 UTC
    Returns a mapping of record IDs to ISO8601 datetime strings.
    """
    schedule: dict[str, str] = {}
    now = datetime.utcnow()
    if cadence in CADENCE_INTERVALS:
        interval = timedelta(**CADENCE_INTERVALS[cadence])
        start = now + interval
    elif cadence == "every_n" and n_days:
        interval = timedelta(days=n_days)
        start = now + interval
    else:
        # default cadence interval
        interval = timedelta(**CADENCE_INTERVALS[DEFAULT_CADENCE])
        start = now + interval

    for idx, rec in enumerate(records):
        dt = start + interval * idx
        dt = dt.replace(
            hour=DEFAULT_PUBLISH_HOUR,
            minute=0,
            second=0,
            microsecond=0,
        )
        schedule[rec["id"]] = dt.isoformat()
    return schedule

@with_fallback(generate_dummy_schedule)
async def propose_schedule_async(
    records: list[dict], cadence: str = "daily", n_days: int | None = None
) -> dict[str, str]:
    """
    Use the Scheduler Agent to propose posting schedule given cadence.
    Falls back to a dummy schedule on failure via decorator.
    """
    logger.info(
        "propose_schedule_async: cadence=%s, n_days=%s, records=%d",
        cadence,
        n_days,
        len(records),
    )
    prompt = json.dumps(
        {
            "cadence": cadence,
            "n_days": n_days,
            "episodes": [
                {"id": rec["id"], "title": rec.get("selected_title"), "description": rec.get("long_description")}
                for rec in records
            ],
        }
    )
    result = await Runner.run(scheduler_agent, prompt)
    schedules = json.loads(result.final_output)
    if not isinstance(schedules, dict):
        raise ValueError("Scheduler agent returned invalid schedule format")
    return schedules