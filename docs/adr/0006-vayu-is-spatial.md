# 6. Vayu's own theme is Spatial

**Status:** Accepted  
**Date:** 2026-11-25

## Context

The `vayu` theme was Catppuccin Mocha with mauve and rose. It looked like a popular terminal theme rather than Vayu's own, and it put colour everywhere: a tint on every tile, mauve for where you are, pink beside it. Nine directions were drawn on the same desktop (liquid glass, spatial, aurora, Material You, clay, soft UI, minimal, poster) and Spatial was chosen.

## Decision

`vayu` becomes Spatial: neutral graphite (no blue or purple cast), dark glass for panels, very round corners, thin rims and more air between windows. Where you are is shown by brightness, not a hue: the accent is a warm near-white (`#f4f4f2`, dark text on it). The hues are soft and kept for meaning only: red danger, green done, yellow waiting, peach look here, plus teal and blue for status. The theme sets `[ui]` too: radius 20, glass 0.44, gaps 8, thin borders.

The old look is still one command away: `varna apply catppuccin-mocha`.

## Consequences

- Every tool that follows the theme becomes Spatial on the next `varna apply`; tools with their own CSS (Vyom and its panels, the websites) adopt the same shapes separately.
- A near-white accent means anything that drew text in the accent colour now draws it white: emphasis comes from weight and brightness.
- Tests that pinned the old colours now pin the new ones.
