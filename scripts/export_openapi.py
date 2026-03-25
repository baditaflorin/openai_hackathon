"""Export the committed OpenAPI artifact for the versioned public API."""
from __future__ import annotations

import json
from pathlib import Path

from clipmato.web import app


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    artifact_path = repo_root / "docs" / "openapi" / "clipmato-v1.openapi.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(artifact_path)


if __name__ == "__main__":
    main()
