#!/bin/sh
set -eu

if [ "${CLIPMATO_CONTENT_BACKEND:-}" = "ollama" ]; then
  OLLAMA_URL="${CLIPMATO_OLLAMA_BASE_URL:-http://ollama:11434}"
  OLLAMA_MODEL="${CLIPMATO_OLLAMA_MODEL:-gpt-oss:20b}"
  echo "Waiting for Ollama at ${OLLAMA_URL}..."
  python - <<'PY'
import json
import os
import sys
import time
import urllib.error
import urllib.request

base_url = os.environ.get("CLIPMATO_OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
model = os.environ.get("CLIPMATO_OLLAMA_MODEL", "gpt-oss:20b").strip()
deadline = time.time() + 180
last_error = "unknown"

while time.time() < deadline:
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=5) as response:
            payload = json.load(response)
        models = payload.get("models") or []
        names = {str(item.get("name") or "").strip() for item in models}
        if model in names:
            sys.exit(0)
        last_error = f"model '{model}' is not available yet"
    except Exception as exc:  # pragma: no cover - container startup path
        last_error = str(exc)
    time.sleep(2)

print(f"Ollama did not become ready in time: {last_error}", file=sys.stderr)
sys.exit(1)
PY
fi

exec "$@"
