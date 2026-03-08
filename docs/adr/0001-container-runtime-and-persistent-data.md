# ADR 0001: Container runtime and persistent data directory

- Status: Accepted (Implemented in v0.1.0)
- Date: 2026-03-08

## Context

Clipmato needs a repeatable container runtime for local development and demos. The application also needs to support `docker run` without relying on the caller's current working directory or writing uploads into an installed package path.

## Decision

Clipmato is packaged as an installable Python project and shipped with a Docker image whose default command starts the FastAPI web app.

Runtime data is separated from application code:

- Templates and static assets continue to load from the installed package.
- Uploads and metadata are written to a configurable data directory controlled by `CLIPMATO_DATA_DIR`.
- The Docker image defaults `CLIPMATO_DATA_DIR` to `/data`.
- Docker Compose uses a named volume mounted at `/data` so the service can be started from the repository and later run with `docker run` from any shell.

## Consequences

- Container startup no longer depends on the repository layout at runtime.
- Uploads and metadata survive container replacement when the named volume is reused.
- Local source checkouts keep the existing default of writing to `clipmato/uploads`, while packaged installs fall back to `~/.clipmato` unless `CLIPMATO_DATA_DIR` is set.
- New runtime environment variables must be documented and preserved in deployment environments.
