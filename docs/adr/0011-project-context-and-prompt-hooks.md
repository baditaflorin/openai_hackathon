# ADR 0011: Project context and prompt hooks for reusable editorial guidance

- Status: Accepted (Implemented in v0.3.0)
- Date: 2026-03-10

## Context

Clipmato currently processes each uploaded file mostly in isolation. The prompt engine sees the raw transcript or artifact, but it does not know whether the episode belongs to a recurring project, series, customer, or editorial lane.

That becomes a quality problem once the same workflow is used for repeatable work such as:

- a series about OpenStreetMap, mapping, or civic data
- a branded content lane with consistent framing
- a project where titles and descriptions should share a tone, angle, or CTA
- a workflow where generated copy needs lightweight prompt guidance before and after the main source material

Without explicit project context, title and description generation treats every upload as a one-off. That weakens consistency and makes it harder to encode reusable knowledge such as topic framing, audience expectations, and editorial hooks.

## Decision

Clipmato will support an optional project context payload on each record and will inject that context into promptable generation tasks through explicit pre-hook and post-hook fields.

Project context rules:

- A record may include a `project_context` object with normalized editorial metadata.
- The first implementation stores project context per record rather than introducing a separate project registry or CRUD surface.
- `project_context` includes:
  - `project_name`
  - `project_summary`
  - `project_topics`
  - `project_prompt_prefix`
  - `project_prompt_suffix`
- Empty project payloads must be discarded so records do not accumulate meaningless blank structures.

Prompt integration rules:

- Promptable tasks that generate outward-facing copy must receive project-aware variables in addition to their core task inputs.
- Project-aware prompt variables include a rendered context block plus explicit prefix and suffix hooks.
- The prefix hook is prepended before the core task material.
- The suffix hook is appended after the core task material.
- The rendered context block summarizes the project name, summary, and topics in a stable format so prompt definitions can use one reusable placeholder.
- Title suggestion, description generation, script generation, and distribution guidance must consume these project-aware variables.

Presentation rules:

- Record presentation helpers must derive compact title and subtitle helper text from `project_context`.
- These helpers should appear in the library and record detail UI to make the governing project context visible to the user.
- The UI should allow users to attach project context at upload time without requiring a dedicated project-management workflow.

Deferred work:

- A reusable project library or template system is explicitly deferred.
- Cross-record project reuse, project editing, and default project selection can be layered on later without changing the prompt contract established here.

## Consequences

- Generated titles and descriptions can stay aligned with a broader series or project instead of only the local transcript.
- Prompt definitions gain a stable mechanism for reusable editorial hooks without hard-coding project-specific instructions.
- Records become more self-describing because the originating project context is stored with the episode.
- The upload flow becomes slightly heavier because it now accepts optional project metadata fields.
- This decision does not yet solve global project reuse; users must currently re-enter or automate the same project payload until a registry exists.
