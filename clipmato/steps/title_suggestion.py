import json
from agents import Runner
from ..agents.title_suggester import title_suggester_agent

def propose_titles(transcript: str) -> list[str]:
    """Use the Title Suggester agent to propose 5 episode titles."""
    result = Runner.run_sync(title_suggester_agent, transcript)
    raw = result.final_output.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines.pop(0)
        if lines and lines[-1].startswith("```"):
            lines.pop(-1)
        raw = "\n".join(lines)
    try:
        titles = json.loads(raw)
        return titles if isinstance(titles, list) else []
    except Exception:
        return [line.strip() for line in raw.splitlines() if line.strip()]

async def propose_titles_async(transcript: str) -> list[str]:
    """Asynchronously use the Title Suggester agent to propose 5 episode titles."""
    result = await Runner.run(title_suggester_agent, transcript)
    raw = result.final_output.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines.pop(0)
        if lines and lines[-1].startswith("```"):
            lines.pop(-1)
        raw = "\n".join(lines)
    try:
        titles = json.loads(raw)
        return titles if isinstance(titles, list) else []
    except Exception:
        return [line.strip() for line in raw.splitlines() if line.strip()]