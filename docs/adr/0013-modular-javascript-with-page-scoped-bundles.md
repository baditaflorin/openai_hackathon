# ADR 0013: Modular JavaScript with Page-Scoped Bundles

- Status: Proposed
- Date: 2026-03-10

## Context

All client-side logic lives in a single 827-line `app.js` file that is loaded on every page. This file contains functionality for at least five distinct features: file upload + drag-and-drop, recording controls (MediaRecorder), project preset management, scheduler cadence toggles, and settings panel visibility. Most pages only need one or two of these feature sets, yet every visitor downloads and parses all 30 KB of JavaScript.

As the app grows, this monolith will become harder to maintain, harder to test in isolation, and slower to parse on lower-powered devices. The single `DOMContentLoaded` handler silently skips features whose DOM nodes are absent, but this pattern makes dead-code elimination impossible for the browser.

## Decision

1. **Split `app.js` into ES modules.** Create a `clipmato/static/modules/` directory with one file per feature area:
   - `upload.js` — drop zone, file picker, XHR upload, queue summary.
   - `recording.js` — MediaRecorder start/stop/format logic.
   - `presets.js` — project preset selector, editor, CRUD forms.
   - `scheduler.js` — cadence toggles, auto-schedule interactions.
   - `settings.js` — backend selector visibility toggles.
   - `cards.js` — episode card creation, update, and polling.
   - `shared.js` — `announce()`, `escapeHtml()`, `setCaptureError()`, busy-form bindings.

2. **Page-scoped entry points.** Each template loads only the modules it needs via `<script type="module">`:
   - `index.html` → `upload.js`, `recording.js`, `presets.js`, `cards.js`, `shared.js`
   - `scheduler.html` → `scheduler.js`, `shared.js`
   - `settings.html` → `settings.js`, `shared.js`
   - `record.html` → `shared.js`

3. **Keep a thin `app.js` shim.** For the transition period, retain a compatibility `app.js` that dynamically imports the modules. Remove it once all templates use `type="module"` imports directly.

4. **No build tool required.** ES modules are natively supported by all modern browsers. Avoid adding Webpack, Vite, or Rollup unless the project later requires JSX, TypeScript, or npm dependencies.

## Consequences

- **Benefits:** Pages parse and execute only the JS they need — up to 70% less JS on the settings page and record detail page. Each module can be tested and reviewed independently. Future contributors can add a feature module without reading 800+ lines.
- **Tradeoffs:** Older browsers without `type="module"` support will not work (IE11 is already unsupported by the app's CSS features). A small number of extra HTTP requests occur, though HTTP/2 multiplexing makes this negligible.
- **Follow-up:** Once modules are stable, add a lightweight bundler for production builds to reduce HTTP round-trips in single-file output.
