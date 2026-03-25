"""Clipmato package metadata."""

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional during bootstrap
    load_dotenv = None
else:
    load_dotenv()

__version__ = "0.4.0"
