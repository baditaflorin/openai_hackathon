# File: clipmato/agents/__init__.py
"""
Clipmato agents package with plugin support.

Drop a new module in this directory defining an Agent instance named *_agent,
and it will be auto-discovered.
"""
import pkgutil
import importlib
from typing import Optional, Dict

__all__ = []
_agents: Dict[str, object] = {}

for _finder, module_name, _ispkg in pkgutil.iter_modules(__path__):
    if module_name.startswith("_"):
        continue
    module = importlib.import_module(f"{__name__}.{module_name}")
    for attr in dir(module):
        if attr.endswith("_agent"):
            agent = getattr(module, attr)
            globals()[attr] = agent
            __all__.append(attr)
            _agents[agent.name] = agent

def list_agents() -> Dict[str, object]:
    """Return mapping of agent display names to Agent instances."""
    return dict(_agents)

def get_agent(name: str) -> Optional[object]:
    """Get an Agent instance by its display name."""
    return _agents.get(name)