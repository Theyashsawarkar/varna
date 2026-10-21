# 4. Reload running tools, but never from a throwaway HOME

**Status:** Accepted  
**Date:** 2026-10-21

## Context

A theme switch should show at once, without restarting anything: sway reloads its config, waybar its style on SIGUSR2, kitty its config on SIGUSR1, tmux re-sources a file per server, Neovim runs a function through `--remote-expr` (never typing into a buffer). But the reloaders find tools through the process table and runtime sockets, not through HOME: a test run with a throwaway HOME once restyled the developer's real tmux and switched the desktop to light mode.

## Decision

`apply` reloads only when HOME is the user's real home (`core.live_home()`, from the password database); otherwise it writes files and reloads nothing. Tools that can't reload live (the prompt, fzf, lazygit, swaylock) take the theme on their next start, and `apply` says so.

## Consequences

- Tests and previews (vinyasa's tests, screenshots) can apply freely.
- Running varna under another HOME on purpose writes files but never touches the session.
