# ADR 0048: Guided setup, readiness, and runtime profiles

- Status: Proposed
- Date: 2026-03-31

## Context

Clipmato already supports multiple execution modes and providers, which is a strength:

- OpenAI-backed transcription and content generation
- local Whisper transcription
- Ollama-backed generation
- Google OAuth credentials for YouTube
- saved runtime profiles and host-native shortcuts

The problem is not capability. The problem is operator friction. Setup is still cognitively heavy because the user has to understand several moving parts before the app can feel smooth:

- which runtime mode they actually want
- whether required binaries and services are installed
- why publishing is blocked
- whether an issue belongs to settings, environment, provider auth, or the current episode

The current settings page exposes real power, but it is closer to an admin panel than a guided setup flow.

## Decision

Clipmato will adopt a guided setup and readiness model.

Readiness model:

- The app computes readiness separately for `capture`, `processing`, `review`, `scheduling`, `publishing`, and `automation`.
- Each capability reports `ready`, `warning`, or `blocked` plus concrete next steps.
- Readiness must be visible both globally and inside episode workspaces.

Setup model:

- The default setup experience is a guided wizard with recommended profiles such as `OpenAI Cloud`, `Local Offline`, and `Hybrid Local + Cloud`.
- Each profile explains tradeoffs in plain language: cost, quality, latency, local dependencies, and publish readiness.
- Diagnostics verify dependencies such as `ffmpeg`, local Whisper availability, Ollama reachability, callback URL validity, and provider connection state.
- The app stores the last successful readiness check and last failing reason for each capability.

UX rules:

- Users should see the shortest path to a working setup before they see advanced fields.
- Advanced runtime inputs remain available, but they move behind an “Advanced configuration” section.
- Episode-level blockers should deep-link back to the exact setup task that resolves them.
- The same readiness vocabulary must be used across home, workspace, scheduler, and settings.

## Consequences

- The experience becomes much easier to use because the app helps users get to a working state instead of just showing fields.
- The difference between “this profile is valid” and “this episode is publish-ready” becomes much clearer.
- Support burden should drop because blockers become more actionable and more visible.
- The app will need a diagnostics layer and some UI restructuring around profiles and readiness cards.
- This is one of the highest-leverage cleanup steps because better setup reduces confusion everywhere else in the workflow.
