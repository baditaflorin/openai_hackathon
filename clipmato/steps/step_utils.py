"""
Utilities for defining agent-based pipeline steps in Clipmato.
Provides generic synchronous and asynchronous runners with optional output parsing.
"""
import json
import logging
from typing import Any, Callable, Optional
from agents import Runner
import re

logger = logging.getLogger(__name__)

def parse_json(raw: str) -> Any:
    """Parse a JSON-encoded string."""
    return json.loads(raw)

def parse_list(raw: str) -> list[Any]:
    """Strip markdown code fences and parse JSON list or fallback to newline-split."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines.pop(0)
            if lines and lines[-1].startswith("```"):
                lines.pop(-1)
            text = "\n".join(lines)
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except Exception:
        return [line.strip() for line in text.splitlines() if line.strip()]

async def run_agent_async(
        agent: Any,
        prompt: str,
        *,
        default: Any = None,
        parse_fn: Callable[[str], Any] = lambda x: x,
) -> Any:
    """
    Run the given agent asynchronously on the prompt and parse the output.
    Default parse_fn returns raw string.
    """
    try:
        result = await Runner.run(agent, prompt)
    except Exception:
        logger.exception("run_agent_async: agent execution failed")
        return default
    raw = result.final_output.strip()
    if not raw:
        logger.warning("run_agent_async: empty output from agent")
        return default
    try:
        return parse_fn(raw)
    except Exception:
        logger.exception("run_agent_async: parsing output failed")
        # Attempt to extract JSON if possible
        json_match = re.search(r'\{.*\}|$$ .* $$', raw, re.DOTALL)
        if json_match:
            try:
                return parse_fn(json_match.group(0))
            except Exception:
                pass
        return default

def run_agent_sync(
        agent: Any,
        prompt: str,
        *,
        default: Any = None,
        parse_fn: Callable[[str], Any] = lambda x: x,
) -> Any:
    """
    Run the given agent synchronously on the prompt and parse the output.
    Default parse_fn returns raw string.
    """
    try:
        result = Runner.run_sync(agent, prompt)
    except Exception:
        logger.exception("run_agent_sync: agent execution failed")
        return default
    raw = result.final_output.strip()
    if not raw:
        logger.warning("run_agent_sync: empty output from agent")
        return default
    try:
        return parse_fn(raw)
    except Exception:
        logger.exception("run_agent_sync: parsing output failed")
        # Attempt to extract JSON if possible
        json_match = re.search(r'\{.*\}|$$ .* $$', raw, re.DOTALL)
        if json_match:
            try:
                return parse_fn(json_match.group(0))
            except Exception:
                pass
        return default
