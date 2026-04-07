# ADR 0052: Single-episode capture-to-publish fast path

- Status: Proposed
- Date: 2026-04-04

## Context

Clipmato already supports the main building blocks of a modern episode workflow:

- browser recording or drag-and-drop upload
- background transcription and content generation
- title, description, and entity suggestions
- scheduling and provider-backed publishing

That is a strong foundation, but the product can still drift into feeling like a collection of utilities instead of one clear job flow. If the primary use case is not stated explicitly, the architecture can become over-optimized for side features while the most common path stays fragmented.

The clearest baseline use case in the current app is simple:

- one operator has one recording
- they want to turn it into a publishable episode quickly
- they need visible progress, lightweight review, and an obvious next step at each stage

## Decision

Clipmato will treat the single-episode capture-to-publish path as a primary product use case.

The supported flow is:

1. capture or upload one audio or video source
2. process it into transcript and generated editorial assets
3. review and select or edit the publishable copy
4. schedule or publish the episode

Product rules for this use case:

- A first-time user must be able to understand the workflow without reading internal concepts such as agents, prompts, or jobs.
- The default path should favor one episode at a time, with progress and blockers shown in user-facing language.
- The operator should be able to complete the episode without needing batch tools or external scripts.
- Runtime blockers, provider blockers, and review blockers must appear inline in the workflow rather than being hidden behind admin-only pages.
- Future architecture changes should preserve a clean fast path even when more advanced multi-episode features are added.

## Consequences

- Clipmato stays grounded in a concrete end-user job instead of becoming a generic media-processing toolbox.
- UX and API decisions can be judged against one clear success path: how quickly one episode reaches ready-to-publish status.
- Bulk planning and automation remain important, but they become extensions of the fast path rather than the center of the product.
- Some advanced workflows may feel intentionally secondary when they conflict with keeping the single-episode journey simple.
