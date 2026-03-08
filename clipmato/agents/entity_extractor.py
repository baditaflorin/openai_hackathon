from agents import Agent
from ..prompts.registry import resolve_prompt_version

_prompt_version = resolve_prompt_version("entity_extraction")

entity_extractor_agent = Agent(
    name=_prompt_version.label,
    instructions=_prompt_version.system_instructions,
)
