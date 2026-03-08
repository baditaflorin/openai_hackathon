from agents import Agent
from ..prompts.registry import resolve_prompt_version

_prompt_version = resolve_prompt_version("title_suggestion")

title_suggester_agent = Agent(
    name=_prompt_version.label,
    instructions=_prompt_version.system_instructions,
)
