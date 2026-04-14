# ADR 0071: Scenario builders, fake adapters, and regression matrices

- Status: Proposed
- Date: 2026-04-14

## Context

ADR 0066 defines the current testing style, but many tests still hand-roll large payloads, patch environment state inline, or only exercise one backend path at a time. That keeps tests readable in small doses, yet it leaves duplication and uneven coverage as runtime combinations multiply.

The repository now needs a more systematic way to express realistic scenarios without turning every test into setup code.

## Decision

Clipmato will standardize reusable scenario builders and fake adapters for deterministic regression coverage.

Test support rules:

- Shared builders will create valid metadata records, runtime settings, project presets, upload fixtures, and publish-job payloads.
- External dependencies such as model providers, schedulers, clocks, and publisher integrations must expose fake adapters suitable for automated tests.
- New integration work is not complete until it has at least one fake or stub collaborator that can drive deterministic tests.

Regression matrix:

- Test suites must cover the important runtime combinations through table-driven or parametrized scenarios rather than ad hoc copy-pasted cases.
- Matrix coverage should include backend selection, readiness blockers, publish states, and retry or failure paths that matter to user-visible behavior.
- Slow end-to-end checks remain valuable, but most regression coverage should be expressed through deterministic component tests built on shared builders and fakes.

## Consequences

- Tests become drier and easier to extend as new providers, routes, and runtime modes are added.
- Backend-specific regressions become easier to catch without requiring network access or heavyweight local setup.
- The repository takes on some upfront maintenance for shared builders and fake adapters, but gains faster and more reliable feedback in return.
