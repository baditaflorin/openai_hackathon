# ADR 0027: Resumable uploads and object-backed media storage

- Status: Proposed
- Date: 2026-03-27

## Context

Clipmato currently accepts uploads through a single request to `/upload`, saves the file into the runtime data directory, and begins background processing afterward. That is fast to build and works for small local demos, but it is not a durable production ingestion model.

The current constraints are already visible in the codebase:

- uploads are capped at 50 MB
- the web app is in the data path for the full media transfer
- storage assumes one writable filesystem
- interrupted transfers require the user to start over

For real users, podcast and video source files are often much larger than the current happy path, and hosted deployments need storage that survives app restarts and horizontal scaling.

## Decision

Clipmato will adopt resumable uploads backed by a storage abstraction whose production default is object storage.

Upload rules:

- Browser and API clients upload through resumable sessions with chunk tracking, upload expiry, and final checksum validation.
- The application creates an upload session first, then accepts chunked transfer directly or through pre-signed URLs depending on the deployment profile.
- Processing jobs start only after the upload session is finalized and the stored object is verified.

Storage rules:

- Object storage is the default production backend for original media and derived artifacts.
- A local filesystem adapter remains supported for single-node development and self-hosted installs.
- The canonical metadata for a media object includes storage key, checksum, content type, size, original filename, and workspace ownership.
- Derived files such as edited audio, thumbnails, or rendered publish assets use the same abstraction instead of ad hoc local paths.

Lifecycle rules:

- Upload sessions, partial chunks, and abandoned objects have explicit cleanup policies.
- Media ingestion events are recorded so users can diagnose stalled or failed uploads.
- Large-file transcoding, validation, and thumbnail extraction run as durable background jobs rather than request-time work.

## Consequences

- Users get a much more reliable upload experience for large or unstable network transfers.
- Hosted deployments gain a storage model that works across multiple web and worker nodes.
- The project must take on multipart upload orchestration, cleanup jobs, and storage cost management.
- Local development remains simple because the filesystem adapter still supports low-friction single-machine use.
