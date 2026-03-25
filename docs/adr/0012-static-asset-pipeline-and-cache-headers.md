# ADR 0012: Static Asset Pipeline and Cache Headers

- Status: Accepted (Implemented in v0.3.0)
- Date: 2026-03-10

## Context

Clipmato serves all static assets (`bootstrap.min.css` at 232 KB, `style.css` at 19 KB, and `app.js` at 30 KB) from FastAPI's `StaticFiles` mount with no cache-control headers, no content hashing, and no compression. Every page load re-downloads all three files. On slower connections or mobile devices this adds 250–300 KB of uncompressed transfer to every navigation.

Bootstrap is vendored as a full copy of `bootstrap.min.css` even though the app uses only a fraction of its classes (mainly grid, form controls, and utilities). The unused CSS constitutes roughly 80% of the file.

There is no gzip or Brotli middleware, so responses are sent at full size regardless of browser capabilities.

## Decision

1. **Content-hashed filenames.** Introduce a lightweight build step (or a Jinja2 helper) that appends a content hash to each static filename (e.g. `style.a1b2c3d4.css`). Set `Cache-Control: public, max-age=31536000, immutable` on files whose names carry a hash. This enables aggressive browser caching while guaranteeing instant cache-busting on deploys.

2. **GZip / Brotli middleware.** Add `GZipMiddleware` from Starlette to the FastAPI app with a minimum size threshold of 500 bytes. This compresses HTML, CSS, and JS responses on the fly.

3. **Trim Bootstrap.** Replace the vendored full `bootstrap.min.css` with either:
   - A PurgeCSS post-process pass that strips unused selectors, or
   - A hand-curated partial import that includes only `_reboot`, `_grid`, `_forms`, `_utilities`, and `_buttons` — the subset Clipmato actually uses.

   Target: reduce Bootstrap payload from 232 KB to ≤ 30 KB.

4. **Preload critical CSS.** Add a `<link rel="preload" as="style">` for `style.css` in `base.html` so the browser fetches the custom stylesheet with highest priority while still downloading Bootstrap.

## Consequences

- **Benefits:** First-paint time drops significantly on repeat visits (assets served from cache). Total transfer for a cold load shrinks by ~200 KB after Bootstrap trimming + gzip. CDN-ready because hashed filenames never collide.
- **Tradeoffs:** A build/hash step adds minor complexity to the deployment pipeline. PurgeCSS requires a safelist when new Bootstrap classes are added.
- **Follow-up:** Monitor Lighthouse performance scores before and after. Consider extracting critical above-the-fold CSS inline for sub-second first contentful paint.
