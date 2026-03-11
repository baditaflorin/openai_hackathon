"""CLI entrypoint for the Clipmato web application."""
from __future__ import annotations

import argparse
import os


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"}


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for host-native and generic web runs."""
    parser = argparse.ArgumentParser(description="Run the Clipmato web application.")
    parser.add_argument(
        "--host",
        default="",
        help="Bind host. Defaults to 127.0.0.1 for --host-native, otherwise CLIPMATO_HOST or 0.0.0.0.",
    )
    parser.add_argument("--port", type=int, default=int(os.getenv("CLIPMATO_PORT", "8000")))
    parser.add_argument("--reload", action="store_true", default=_truthy_env("CLIPMATO_RELOAD"))
    parser.add_argument(
        "--host-native",
        action="store_true",
        help="Optimize defaults for a macOS/Linux host-native run instead of Docker.",
    )
    parser.add_argument("--data-dir", default=os.getenv("CLIPMATO_DATA_DIR", ""))
    parser.add_argument("--transcription-backend", default=os.getenv("CLIPMATO_TRANSCRIPTION_BACKEND", ""))
    parser.add_argument("--content-backend", default=os.getenv("CLIPMATO_CONTENT_BACKEND", ""))
    parser.add_argument("--whisper-model", default=os.getenv("CLIPMATO_LOCAL_WHISPER_MODEL", ""))
    parser.add_argument("--whisper-device", default=os.getenv("CLIPMATO_LOCAL_WHISPER_DEVICE", ""))
    parser.add_argument("--ollama-base-url", default=os.getenv("CLIPMATO_OLLAMA_BASE_URL", ""))
    parser.add_argument("--ollama-model", default=os.getenv("CLIPMATO_OLLAMA_MODEL", ""))
    parser.add_argument(
        "--ollama-timeout",
        type=int,
        default=int(os.getenv("CLIPMATO_OLLAMA_TIMEOUT_SECONDS", "120")),
    )
    return parser


def _apply_runtime_env(args: argparse.Namespace) -> None:
    if args.host_native:
        os.environ.setdefault("CLIPMATO_HOST", "127.0.0.1")
        os.environ.setdefault("CLIPMATO_TRANSCRIPTION_BACKEND", "local-whisper")
        os.environ.setdefault("CLIPMATO_CONTENT_BACKEND", "ollama")
        os.environ.setdefault("CLIPMATO_LOCAL_WHISPER_DEVICE", "mps")
        os.environ.setdefault("CLIPMATO_OLLAMA_BASE_URL", "http://localhost:11434")

    explicit_values = {
        "CLIPMATO_HOST": args.host,
        "CLIPMATO_PORT": str(args.port),
        "CLIPMATO_TRANSCRIPTION_BACKEND": args.transcription_backend,
        "CLIPMATO_CONTENT_BACKEND": args.content_backend,
        "CLIPMATO_LOCAL_WHISPER_MODEL": args.whisper_model,
        "CLIPMATO_LOCAL_WHISPER_DEVICE": args.whisper_device,
        "CLIPMATO_OLLAMA_BASE_URL": args.ollama_base_url,
        "CLIPMATO_OLLAMA_MODEL": args.ollama_model,
        "CLIPMATO_OLLAMA_TIMEOUT_SECONDS": str(args.ollama_timeout),
        "CLIPMATO_DATA_DIR": args.data_dir,
    }
    for key, value in explicit_values.items():
        if str(value or "").strip():
            os.environ[key] = str(value).strip()


def run(argv: list[str] | None = None) -> None:
    """Launch the FastAPI app with runtime-configurable host/Ollama/Whisper settings."""
    import uvicorn

    parser = build_parser()
    args = parser.parse_args(argv)
    _apply_runtime_env(args)
    host = os.getenv("CLIPMATO_HOST") or "0.0.0.0"
    port = int(os.getenv("CLIPMATO_PORT", "8000"))
    uvicorn.run("clipmato.web:app", host=host, port=port, reload=args.reload)


if __name__ == "__main__":
    run()
