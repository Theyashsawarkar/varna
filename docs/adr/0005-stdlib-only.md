# 5. Standard library only

**Status:** Accepted  
**Date:** 2026-10-21

## Context

varna runs at login (`varna ensure`, before waybar and mako start) and from keybindings and panels; a missing dependency there means a desktop without a bar or notifications.

## Decision

Python 3.11's standard library only: `tomllib` for themes, a small regex renderer for templates (no Jinja), `subprocess` and signals for reloads.

## Consequences

- `git clone` and a symlink are a full install.
- The template language stays small: names, filters, fallbacks, line conditions. That's enough for colour files and keeps typos detectable.
