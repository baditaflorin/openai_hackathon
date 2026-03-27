# ADR 0031: Timezone-safe scheduling and locale-aware publishing

- Status: Proposed
- Date: 2026-03-27

## Context

Clipmato already lets users assign publish dates and auto-generate schedules, but the current scheduling logic defaults to UTC and applies a fixed publish hour. That is simple internally, yet it does not match how real users think about release times.

Scheduling is a user-trust feature. If the product shows one time, stores another, or shifts unexpectedly at daylight-saving boundaries, users will stop trusting automation.

The existing implementation shows the gap clearly:

- schedule proposals are generated from `datetime.now(UTC)`
- publish defaults use a single hour constant
- there is no first-class timezone or locale model attached to a schedule

## Decision

Clipmato will treat timezone and locale as first-class scheduling data.

Scheduling rules:

- Every scheduled publish stores the canonical UTC instant plus the originating IANA timezone and the user-facing local wall-clock time that was chosen.
- API contracts reject naive datetimes for user-authored schedules.
- Recurring schedule logic uses timezone-aware recurrence rules so daylight-saving transitions are handled predictably.

UX rules:

- The UI defaults to the workspace or user timezone, while always making the effective timezone visible near date and time inputs.
- Schedule previews show the local publish time, the UTC equivalent, and any daylight-saving shift that affects the next occurrence.
- Notifications, calendars, and export files use locale-aware formatting so users see dates in a familiar format.

Operational rules:

- Historical records keep their original timezone context for auditability even if the workspace default changes later.
- Provider adapters receive explicit publish instants and timezone metadata instead of inferring them from server-local time.
- Test coverage must include daylight-saving boundaries, timezone changes, and locale-formatting regressions.

## Consequences

- Users get a scheduling experience that matches how they actually plan releases.
- Publish automation becomes safer across regions, hosted deployments, and daylight-saving changes.
- The system must carry more datetime metadata and maintain timezone-aware validation across API, UI, and workers.
- Some existing UTC-only assumptions will need migration work, but the resulting behavior will be much less surprising.
