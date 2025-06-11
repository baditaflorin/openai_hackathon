"""
Clipmato pipeline steps with plugin support.

Drop a new module in this directory defining step functions,
and they will be auto-discovered.
"""
import pkgutil
import importlib

__all__ = []

_SKIP_MODULES = {"step_utils"}

for _finder, module_name, _ispkg in pkgutil.iter_modules(__path__):
    if module_name in _SKIP_MODULES or module_name.startswith("_"):
        continue
    module = importlib.import_module(f"{__name__}.{module_name}")
    for attr in dir(module):
        if attr.startswith("_"):
            continue
        obj = getattr(module, attr)
        if callable(obj) and getattr(obj, "__module__", None) == module.__name__:
            globals()[attr] = obj
            __all__.append(attr)