# 3. Every theme fills the same 26 colours, plus roles

**Status:** Accepted  
**Date:** 2026-10-21

## Context

Templates need to name colours. If each theme used its own names (Rosé Pine's "love" and "iris", Nord's "frost"), every template would need a branch per theme. Tools also need meanings, not just colours: which colour is the accent, which marks danger, which is text on a coloured capsule.

## Decision

Every theme maps its colours onto the same 26 names (Catppuccin's: crust ... text, rosewater ... lavender), the most widely used set. On top, roles (`accent`, `accent2`, `border`, `urgent`, `ink`, `fg`, `line`, `match`, `ok`, `warn`, `error`...) name what a colour is for; a theme sets any of them to a palette name, another role or a hex, and the rest default. A theme may add colours for one tool (`[tools.tmux]`); templates reach them with a fallback (`{{window_idle|overlay1}}`).

## Consequences

- A template written once works with every theme; the tests render every theme through every template.
- Porting a theme means mapping its colours onto the 26 slots, a judgement call for themes with fewer colours.
- A theme can reproduce an exact existing look (Vayu's) through roles and per-tool extras.
