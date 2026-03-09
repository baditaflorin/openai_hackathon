# ADR 0010: Runtime settings and provider credentials for local and cloud execution

- Status: Accepted (Implemented in v0.3.0)
- Date: 2026-03-08

## Context

Clipmato now supports multiple runtime paths, but the configuration story is still fragmented across environment variables and deployment-time assumptions.

The product needs a settings model that supports:

- local AI execution with selectable backends such as local Whisper and Ollama
- cloud execution with user-provided OpenAI credentials and connected provider accounts such as Google/YouTube
- a consistent way to point the app at external services like an Ollama server
- Docker-based startup paths where optional local AI services can be brought up as part of the stack
- secure storage for secrets so API keys and OAuth tokens are not mixed into record metadata

Without a proper settings system, Clipmato will remain difficult to operate across laptops, local demo machines, Docker deployments, and hosted multi-user environments.

## Decision

Clipmato will introduce a first-class runtime settings system with separate scopes for deployment defaults, user preferences, and stored credentials.

Configuration model:

- Deployment settings remain environment-variable based and define instance-wide defaults, OAuth client configuration, storage paths, and feature flags.
- User settings are persisted separately from episode metadata and define the preferred transcription backend, preferred content backend, model choices, and endpoint overrides.
- Credentials and provider tokens are stored in a dedicated secrets store under the runtime data directory for self-hosted installs, and in an encrypted-at-rest provider for hosted/cloud deployments.
- Secrets must never be written into `metadata.json`, prompt run ledgers, or general-purpose logs.

Runtime selections:

- Transcription backend options will include at least `openai` and `local-whisper`.
- Content backend options will include at least `openai`, `local-basic`, and `ollama`.
- Ollama settings will include a base URL, model name, request timeout, and optional embedding/chat model separation if later needed.
- Local Whisper settings will include model name and device preference, with host-native Apple `mps` support kept as a host runtime concern rather than a Docker Desktop assumption.

Settings precedence:

1. User-saved runtime settings
2. Deployment-level environment defaults
3. Application defaults

Provider credentials:

- Users may save their own OpenAI API key for content and transcription where the deployment allows user-supplied credentials.
- Google OAuth remains deployment-configured at the application level for client ID, client secret, and redirect base URL.
- Per-user Google/YouTube access tokens are stored as user-owned provider credentials and may be revoked or refreshed independently of app-wide settings.
- Hosted/cloud deployments must expose UI flows for connecting, rotating, and deleting saved credentials.

Docker integration:

- Clipmato will support Compose profiles or equivalent optional services so the app can run with integrated local AI dependencies such as Ollama.
- The web app image will support build targets or extras for local AI dependencies so self-hosted operators can build an image with local Whisper support when appropriate.
- Dockerized local Whisper support is intended for CPU and Linux/NVIDIA GPU environments.
- On macOS, Apple Silicon `mps` acceleration remains a host-native path because Docker Desktop Linux containers do not provide direct access to the Apple GPU runtime.

UI direction:

- Clipmato will gain a dedicated Settings area for runtime backends, model selection, service endpoints, and provider credentials.
- Settings pages must distinguish clearly between non-secret preferences and secret values.
- Runtime status panels should read from resolved settings so users can see which backend is active and whether the required credentials are available.

## Consequences

- Clipmato gets a stable operational model across self-hosted, Dockerized, and cloud environments.
- Users can switch between OpenAI, Ollama, and local Whisper without editing environment variables for every run.
- The codebase will need a new settings persistence layer, secret storage abstraction, and settings UI.
- Docker packaging will become more explicit about which images include optional AI dependencies.
- The project must define migration rules from the current env-only configuration model into persisted runtime settings.
