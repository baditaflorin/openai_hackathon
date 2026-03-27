# ADR 0039: Media preview cards and immersive detail surfaces

- Status: Proposed
- Date: 2026-03-27

## Context

Clipmato works on media, but much of the interface still presents episodes as text-heavy utility records. To feel more premium and more immediately understandable, the product should expose richer previews without cluttering the overall UI.

Users should be able to recognize an episode quickly from a visual and structural summary before opening it.

## Decision

Clipmato will make media preview a first-class part of the library and record experience.

Library rules:

- Episode cards show one clean visual preview area such as artwork, waveform, poster frame, or branded placeholder instead of multiple competing thumbnails.
- Cards emphasize the selected title, current workflow stage, and one or two supporting metadata points rather than full metadata dumps.
- Preview surfaces use consistent aspect ratios and consistent corner treatment so the library feels orderly.

Detail rules:

- Record detail uses an immersive top preview surface with integrated playback controls and contextual actions nearby.
- Transcript, generated assets, and publish controls support the media preview rather than visually overpowering it.
- Hover, focus, and selected states on preview elements remain subtle and aligned with the minimalist material system.

## Consequences

- The product feels more like a polished media workspace and less like a generic CRUD dashboard.
- Users can orient faster in the library because each record has a more memorable visual summary.
- Teams must invest in fallback artwork, media extraction, and preview-safe loading states.
- Rich previews increase the need for disciplined layout restraint so the UI stays elegant.
