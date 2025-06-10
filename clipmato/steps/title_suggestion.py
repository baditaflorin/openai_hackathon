import json
import json
from ..agents.title_suggester import title_suggester_agent
from .step_utils import run_agent_async, run_agent_sync, parse_list


def propose_titles(transcript: str) -> list[str]:
    """Use the Title Suggester agent to propose 5 episode titles."""
    return run_agent_sync(
        title_suggester_agent,
        transcript,
        default=[],
        parse_fn=parse_list,
    ) or []


async def propose_titles_async(transcript: str) -> list[str]:
    """Asynchronously use the Title Suggester agent to propose 5 episode titles."""
    return await run_agent_async(
        title_suggester_agent,
        transcript,
        default=[],
        parse_fn=parse_list,
    ) or []