# ADR 0015: Virtual Scrolling and Lazy Rendering for the Episode Library

- Status: Proposed
- Date: 2026-03-10

## Context

The index page renders every episode card server-side via Jinja2 and sends the full HTML to the browser in one response. With a growing library, this creates two scaling problems:

1. **Server cost:** The `/` route reads all records from `metadata.json`, enriches each with progress data, builds project-preset context, and renders the complete template. For N episodes, both CPU and memory usage grow linearly on every page load.

2. **Browser cost:** The DOM contains all episode-card nodes immediately. For 50+ episodes, layout and paint time become noticeable, especially on mobile devices or low-powered laptops. The `episode-grid` CSS grid recalculates geometry for every card even if most are off-screen.

The scheduler page already downloads records via a separate API call and renders them client-side, proving that a JSON-driven rendering path is viable.

## Decision

1. **Paginated API endpoint.** Add `GET /api/episodes?page=1&per_page=20&status=all` that returns a JSON array of episode summaries. The endpoint supports optional filters (`status`, `search` query). Default page size is 20.

2. **Infinite-scroll rendering.** On the index page, render only the first batch of episode cards. Attach an `IntersectionObserver` to a sentinel element at the bottom of the grid. When visible, fetch the next page and append cards to the DOM using the same `createJobCard` / `updateCard` functions already in `app.js`.

3. **Skeleton loading placeholders.** While the next page is being fetched, display 3 skeleton card elements with pulsing CSS animation so the user perceives constant progress rather than a blank gap.

4. **Server-side limit.** The Jinja2 template embeds only the first page of records directly in the HTML for instant first paint and SEO (search engines see content immediately). Subsequent pages are fetched client-side.

5. **Search and filter bar.** Add a lightweight text input above the episode grid that client-side-filters the visible cards by title/filename. When the user types, already-loaded cards are shown/hidden instantly; if none match, a server request with `?search=` is fired.

## Consequences

- **Benefits:** Initial HTML size stays constant regardless of library size. The browser only creates DOM nodes for visible + buffered cards, keeping layout cost O(1) per scroll frame. Users with hundreds of episodes see a fast, responsive library.
- **Tradeoffs:** SEO crawlers only see the first page unless the paginated API is separately indexed. IntersectionObserver is not available in very old browsers (but Clipmato already requires ES2020+).
- **Follow-up:** Consider adding sort controls (by date, by title, by processing status). Add keyboard shortcuts (e.g. `j`/`k`) for fast episode navigation.
