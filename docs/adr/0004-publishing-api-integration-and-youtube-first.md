# ADR 0004: Publishing API integration with YouTube-first rollout

- Status: Accepted (Implemented in v0.2.0)
- Date: 2026-03-08

## Context

Clipmato already lets users pick publish targets and assign scheduled publish times, but that data is only stored locally. The product now needs a path from scheduled content to actual platform delivery.

The first near-term publishing target is YouTube. At the same time, the architecture should not hard-code YouTube-specific logic into the scheduler because additional providers such as Spotify or Apple Podcasts may be added later.

The integration also needs to handle real-world publishing concerns:

- user authorization with third-party platforms
- scheduled execution outside the request/response cycle
- retryable failures and publish status visibility
- provider-specific metadata without breaking the shared scheduling model

## Decision

Clipmato will adopt a provider-based publishing architecture, with YouTube as the first implementation.

Core rules:

- Scheduling remains provider-agnostic and continues to store `schedule_time` plus selected `publish_targets`.
- Actual publishing is executed by provider adapters behind a shared publishing interface rather than directly inside scheduler routes.
- The first adapter will target YouTube uploads and metadata updates.
- Provider integrations must use user-authorized API credentials, not a single shared global account.
- Publishing work must run asynchronously in background jobs so web requests only create or update publish intents.

Planned model:

- `publish_targets` remains the user-facing selection field.
- each record gains provider-specific publish state such as `pending`, `scheduled`, `publishing`, `published`, and `failed`
- each publish attempt records timestamps, provider response identifiers, and last error details
- YouTube-specific fields such as video title, description, privacy status, thumbnail path, and remote video ID are stored in provider-scoped metadata instead of mixed into generic scheduler fields

Execution flow:

1. A user selects YouTube as a publish target and saves a schedule.
2. Clipmato creates a publish intent for the YouTube provider.
3. A background publisher picks up intents whose scheduled time has arrived.
4. The YouTube adapter performs authenticated upload and metadata configuration.
5. Clipmato stores the resulting provider ID and final publish state for auditability and later retries.

YouTube-specific rollout constraints:

- YouTube is the only provider implemented first.
- OAuth-based user connection is required before scheduling YouTube publication.
- Uploads and metadata updates use the YouTube API through a dedicated provider module.
- Thumbnail upload, playlist assignment, and post-publish updates are allowed as follow-on features, not required for the first implementation.

## Consequences

- The current scheduler UI can evolve into real publishing without being rewritten around one provider.
- YouTube work can ship first while keeping a clean extension point for Spotify and Apple Podcasts later.
- Provider credentials and token refresh become a new operational concern and must be stored securely.
- Publishing now requires durable job execution and retry logic instead of request-scoped processing.
- Metadata will become more structured because generic record data and provider-specific publish data must be separated clearly.
