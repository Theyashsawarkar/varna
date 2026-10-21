# 2. Tools include a generated file; varna never rewrites their configs

**Status:** Accepted  
**Date:** 2026-10-21

## Context

A theme switcher can either rewrite each tool's config (search and replace colour values), own each tool's config entirely, or have each config include a small file of colours. Rewriting configs fights with the user's own edits and with dotfile managers; owning them takes the user's config away.

## Decision

Every tool varna themes includes one file varna generates (`~/.local/state/varna/<tool>`): sway's `include`, waybar's `@import`, tmux's `source-file`, kitty's `include`, mako's `include=`, Vyom's `css`, a Lua module for Neovim, `source` for the prompt and fzf, `LG_CONFIG_FILE` for lazygit, command-line options for swaylock. The tool's config keeps its own values before the include as a fallback. Files no tool can include (waybar's Pango markup) go through user templates rendered to their destination.

## Consequences

- The user's configs stay theirs and keep working without varna.
- Each tool needs a one-line hook; `varna doctor` checks it and prints the line.
- Two tools refuse to start when the included file is missing (waybar, mako): `varna ensure` writes missing files at login.
