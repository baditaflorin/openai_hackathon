# ADR 0040: Guided settings with simple and advanced modes

- Status: Proposed
- Date: 2026-03-27

## Context

Clipmato's settings surface is powerful, but that power can work against simplicity when every deployment option is visible at once. A minimalist product should feel easy for first-time users without frustrating advanced operators.

ADR 0025 already proposes onboarding and preflight checks. This ADR focuses on the visual and interaction shape of settings once users are inside the product.

## Decision

Clipmato will organize settings into simple and advanced modes with guided defaults.

Settings rules:

- Default settings views show only the recommended controls required to achieve a working setup.
- Advanced controls live behind an explicit expansion or mode switch rather than appearing inline by default.
- Each settings group begins with a human-readable summary of current state before showing raw fields.

Interaction rules:

- Connection status, health checks, and recommended presets are shown beside the relevant settings instead of in a separate diagnostic page.
- Groups are organized by user intent such as `Transcription`, `Content generation`, `Publishing`, and `Storage`, not by low-level implementation detail.
- Search and jump links are supported so users can reach a specific settings area quickly without scanning a long page.

## Consequences

- The app becomes easier to set up because the default view shows the shortest successful path.
- Power users still retain access to deeper control without forcing that complexity onto everyone else.
- Settings components will need stronger information architecture and summary states.
- Teams must actively prevent simple mode from becoming just a visually compressed version of the full form.
