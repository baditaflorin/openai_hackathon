# ADR 0009: Prompt engine for versioned content generation

- Status: Accepted (Implemented in v0.2.0)
- Date: 2026-03-08

## Context

Clipmato already depends on prompts for important product outcomes such as title suggestions, short and long descriptions, scripts, and other generated content. Those prompts currently live close to the code that uses them, which is simple at first but becomes weak once the team starts optimizing for quality and consistency.

The product now needs a way to answer operational questions such as:

- which title prompt version produces the best click-worthy titles
- which description prompt best respects tone, length, and formatting rules
- which prompts are producing schema violations or low-quality outputs
- when a prompt change improved or degraded results
- how to promote a better prompt without losing traceability

If prompts remain hard-coded and unversioned, Clipmato will not be able to improve generation quality in a disciplined way.

## Decision

Clipmato will adopt a prompt engine with explicit versioning, task-specific prompt definitions, output contracts, and evaluation hooks.

Core rules:

- Prompts for generation tasks such as titles, descriptions, scripts, entities, and future publishing copy must be defined as first-class prompt assets rather than ad hoc inline strings.
- Every prompt asset must have a stable task key, a version identifier, and metadata such as purpose, owner, status, and creation date.
- Prompt definitions must support structured fields such as system instructions, user template, variable inputs, expected output format, and optional schema or formatting constraints.
- Every generation result must record which prompt version produced it, together with the model/backend used at execution time.
- Clipmato must support running multiple prompt versions for the same task so the team can compare output quality over time.
- Each promptable task must have one promoted default prompt version for normal production use.
- Experimental prompt versions may be evaluated in controlled rollout modes such as manual selection, percentage split, shadow runs, or offline replay.
- Prompt outputs must be checked against explicit contracts where possible, such as JSON schema, length limits, forbidden phrases, title count, or formatting rules.
- Prompt quality signals such as user selection, publish performance, validation failures, retries, and editorial edits should be retained as evaluation data for later comparison.
- Prompt changes must be auditable and reviewable like code changes, even if prompt bodies eventually move into a separate prompt registry.

Planned model:

- a `task` identifies the product function, for example `title_suggestion`, `description_generation`, or `script_generation`
- a `prompt_version` identifies one concrete prompt definition for that task
- a `prompt_run` stores the inputs, chosen prompt version, backend/model, output, validation result, and timing
- a `prompt_evaluation` stores later signals such as whether a suggested title was selected, whether a description needed manual cleanup, or whether formatting passed automated checks

Execution flow:

1. A Clipmato step requests generation for a task such as `title_suggestion`.
2. The prompt engine resolves the active prompt version for that task.
3. The engine renders the prompt with the task inputs and declared output contract.
4. The selected backend/model executes the request.
5. The result is validated against task-specific rules.
6. The prompt version, output, and validation status are stored for later analysis.
7. Downstream user behavior and editorial actions can be attached as evaluation signals.

## Consequences

- Prompt tuning becomes measurable instead of anecdotal.
- The team will be able to compare prompt variants for titles, descriptions, and other copy without losing history.
- Generated outputs become easier to debug because prompt version and validation state are attached to each run.
- The codebase will gain a new configuration and persistence layer for prompt assets, prompt runs, and evaluation signals.
- Some generation steps will need refactoring so they call the prompt engine instead of embedding prompt text directly.
- The system will need clear rules for retaining or redacting prompt inputs and outputs when they contain sensitive user content.
