"""CLI entrypoint for the Clipmato web application."""
import os

import uvicorn


def run() -> None:
    """Launch the FastAPI app with environment-configurable host/port."""
    host = os.getenv("CLIPMATO_HOST", "0.0.0.0")
    port = int(os.getenv("CLIPMATO_PORT", "8000"))
    reload = os.getenv("CLIPMATO_RELOAD", "").lower() in {"1", "true", "yes", "on"}
    uvicorn.run("clipmato.web:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run()
