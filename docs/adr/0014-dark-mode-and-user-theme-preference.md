# ADR 0014: Dark Mode and User Theme Preference

- Status: Proposed
- Date: 2026-03-10

## Context

Clipmato's design system (ADR 0005) defines a warm, earthy light palette with CSS custom properties in `:root`. Every surface, text colour, and shadow references these tokens, which is excellent for maintainability — but there is no dark-mode variant. Users who work in low-light environments or who prefer dark UIs in their OS settings see a bright, high-contrast interface that causes eye strain during extended editing sessions.

The existing design system already uses CSS custom properties for all colour decisions (`--bg-page`, `--ink-base`, `--brand-strong`, etc.), so adding a second theme is primarily a matter of redefining these tokens rather than rewriting component styles.

## Decision

1. **Define a dark token set.** Add a `@media (prefers-color-scheme: dark)` block in `style.css` that overrides every colour custom property in `:root`. Use deep, cool-toned neutrals (e.g. `--bg-page: #161b1f`, `--bg-panel: rgba(30, 35, 42, 0.94)`) and desaturated brand accents to maintain the editorial feel without harsh contrast.

2. **Manual toggle with persistence.** Add a small sun/moon toggle button in the `shell-header` (after the workflow-nav). Clicking it sets `data-theme="dark"` on `<html>` and persists the choice in `localStorage`. A matching CSS rule `[data-theme="dark"]` re-applies the dark tokens, overriding the OS-level media query when the user explicitly chooses.

3. **Respect OS preference by default.** On first visit (no stored preference), honour `prefers-color-scheme`. Once the user clicks the toggle, that explicit choice takes priority.

4. **Image and shadow adjustments.** In dark mode, reduce `box-shadow` opacity to avoid glowing edges on panels, and add `filter: brightness(0.92)` to any embedded images that appear too bright against a dark background.

5. **Settings page integration.** Add a "Theme" row in `/settings` that shows the current choice (System / Light / Dark) and lets users change it without using the small header toggle.

## Consequences

- **Benefits:** Immediate accessibility win for light-sensitive users. Modern, premium feel that aligns with user expectations of 2026-era web apps. No structural HTML changes needed — the entire toggle is a CSS token swap plus a few lines of JS.
- **Tradeoffs:** Designers need to audit every surface for sufficient contrast (WCAG AA) in both modes. Screenshots and documentation that show the UI will need two variants or will pick one as canonical.
- **Follow-up:** Extend the theme to the `scheduler.html` calendar widget. Consider a high-contrast accessibility theme as a third option.
