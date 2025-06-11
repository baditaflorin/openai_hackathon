"""
API router modules for web app endpoints.

Drop a new module defining a FastAPI `router` instance to have it included automatically.
"""
import pkgutil
import importlib

__all__ = []
routers = []

for _finder, module_name, _ispkg in pkgutil.iter_modules(__path__):
    if module_name.startswith("_"):
        continue
    module = importlib.import_module(f"{__name__}.{module_name}")
    if hasattr(module, "router"):
        routers.append(module.router)
        __all__.append(module_name)

def list_routers() -> list:
    """Return list of FastAPI routers discovered in this package."""
    return list(routers)