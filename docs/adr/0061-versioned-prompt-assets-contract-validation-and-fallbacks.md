# ADR 0061: Versioned prompt assets, contract validation, and fallbacks

- Status: Accepted (Current repository convention)
- Date: 2026-04-07

## Context

Prompt-driven behavior now powers several core tasks in Clipmato:

- title suggestion
- description generation
- entity extraction
- script generation
- distribution copy generation

Prompt logic can easily become opaque when instructions, model selection, validation, and fallback behavior are scattered across the codebase. Clipmato already has the pieces of a cleaner model, but that model should be stated clearly for onboarding.

## Decision

Clipmato will treat prompt execution as a contract-backed asset pipeline.

Prompt rules:

- Prompt definitions live as packaged JSON assets in `clipmato/prompts/definitions`.
- `clipmato/prompts/registry.py` resolves the active version for each task, including rollout and environment overrides.
- `clipmato/prompts/engine.py` renders prompt variables, executes the selected backend, validates output against the declared contract, applies policy checks, and records prompt-run history.
- Task-facing step modules call the prompt engine and provide explicit local fallback outputs so the workflow can degrade safely.
- When prompt metadata should be preserved on a record, step helpers return both the user-facing output and a compact prompt-run summary.

## Consequences

- Prompt behavior becomes inspectable and reviewable without hardcoding long prompt strings inside business logic.
- Failed or unsafe model output can fall back predictably instead of breaking the whole workflow.
- Contributors must keep prompt contracts and fallback behavior synchronized, because prompt text alone is not the contract.
