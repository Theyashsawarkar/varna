# Changelog

Newest first. Releases are tags (`vX.Y.Z`) with `VERSION` in `varna/__init__.py`.

## v0.1.10 -- 2026-10-24

- **zathura** (the PDF viewer): its colours, and pages recoloured to the
  theme with their hues kept (Ctrl+r shows the original). Include
  `../../.local/state/varna/zathurarc` at the end of your zathurarc
  (zathura reads it relative to the file and expands no `~`).

## v0.1.9 -- 2026-10-24

- **One glass for every panel.** A new `ui.glass` (default 0.55) is the
  background opacity of every floating panel: Vyom's (through its
  vyom.css), nāda's, vinyasa's and the notifications (mako), so they look
  alike in every theme. They used three different values (0.55, 0.62,
  0.85), and vinyasa used `ui.opacity`, which is the terminal's.
- Notifications use the interface font (`ui.font`), like the panels, not
  the monospace one.
- tmux popups and menus, and the fzf pickers inside them, are framed in
  the theme's accent like every other popup (they used the second accent).
- `varna set` checks numbers: `ui.opacity` and `ui.glass` between 0 and 1,
  nothing negative, and a clear error for a value that isn't a number (it
  was a Python traceback).

## v0.1.8 -- 2026-10-24

- **tmux bar colours that never collide.** The bar filled every capsule
  with its own colour, about 12 at once, and themes have 6 to 8: in Rosé
  Pine the current window and the Claude usage capsule were the same teal,
  PRs the session's purple, "Claude waiting" nearly "usage full" (41 such
  pairs across the 10 themes). The template now has the roles for a bar
  where only "look here" capsules are solid (`@prefix`, `@copy`, `@window`,
  `@attention`, plus `@accent` and `@error`) and the rest are soft pills
  (`@soft_bg`, `@soft_fg`, `@soft_dim`; `@warn_bg` tints a warning pill).
  Gruvbox, Nord, Rosé Pine, Tokyo Night, Everforest and Vayu set
  `[tools.tmux]` overrides where their own colours are too close, and a test
  checks every theme keeps the solid capsules apart. `@peach` and `@sage`
  stay, as the prefix and copy-mode colours, for older tmux configs.

## v0.1.7 -- 2026-10-21

- **Popup frames you can see**: a new `frame` role (overlay1 by default)
  draws the boxes inside popups (fzf's list, preview, footer and header
  borders, lazygit's inactive panels, btop's boxes); they used `line`,
  which nearly vanished on a transparent popup in themes like Rosé Pine.
  `VARNA_RGB_FRAME` for scripts.
- Rosé Pine, Dawn and Kanagawa use their own muted colour (overlay1) for
  muted text, which was too dark to read on glass.
- **btop** follows the theme: `btop -c ~/.local/state/varna/btop.conf`
  (varna sets the theme in it; btop keeps its other settings there).

## v0.1.6 -- 2026-10-21

- Scripts can colour their own output from the theme: `fzf.sh` also exports
  `VARNA_RGB_<NAME>` (`r;g;b`) for the accents, text, muted, line, ok / warn
  / error and the main palette colours, e.g. `printf '\e[38;2;%sm'
  "$VARNA_RGB_ACCENT"`. A new template filter, `:semi`, writes `r;g;b`.

## v0.1.5 -- 2026-10-21

- Rosé Pine and Dawn colour tmux's dev servers capsule rose, so it no
  longer matches the green of a status capsule (their green, teal and sky
  are all foam).

## v0.1.4 -- 2026-10-21

- tmux gets more colours from the theme: `@attention` (peach: something
  waits for you), `@dev` (sky: dev servers) and `@ok` / `@warn` / `@error`
  (status capsules that go green, yellow, red).

## v0.1.3 -- 2026-10-21

- Rosé Pine's and Dawn's second accent is foam (their cyan) instead of
  rosewater, which sat too close to iris: the current tmux window, the
  active pane, popups, the prompt's folder and fzf's highlights.

## v0.1.2 -- 2026-10-21

- Vayu's second accent is pink (`#f5c2e7`, Catppuccin's pairing with its
  mauve) instead of the dusty rose left over from the old tmux palette: the
  current tmux window, the active pane, popups, menus, the prompt's folder
  and fzf's highlights.

## v0.1.1 -- 2026-10-21

- The focused window's border is the theme's accent in every theme (Vayu
  used red, Rosé Pine and Dawn their rose), so it matches the active
  workspace, the tmux session and the rest of the highlights.

## v0.1.0 -- 2026-10-21

The first release: one theme for every tool.

- **Themes** are TOML files: a 26-colour palette (Catppuccin's names),
  roles (accent, second accent, border, urgent, ink...), ui values (fonts,
  radius, opacity, gaps, border width) and optional per-tool extras. Ten
  shipped: Vayu, Catppuccin Mocha / Latte, Rosé Pine / Dawn, Tokyo Night,
  Gruvbox, Nord, Kanagawa, Everforest.
- **Twelve tools**: sway, waybar, tmux, kitty, mako, Vyom, Neovim,
  powerlevel10k, fzf, lazygit, swaylock and GTK apps (opt-in), plus
  `palette.json` for any program. Each tool includes one generated file;
  `varna apply` writes them all and reloads what's running (every tmux
  server, kitty window and Neovim, sway, waybar, mako, Vyom).
- **Per-tool themes** (`varna tool nvim tokyo-night`), accent override
  (`varna set accent blue`), light/dark twins (`varna mode toggle`), and the
  desktop's dark/light signal for apps that follow it.
- **Your own themes** (`varna new`, `varna edit`, `varna delete`) and **any
  file as a template** (`varna template add`), with filters (`:a=0.35`,
  `:rgb`, `:alpha=0.4`, `:mix=`), fallbacks (`{{a|b}}`) and line conditions
  (`?swayfx`). Unknown names are errors.
- `varna doctor` checks every theme and prints the line each tool's config
  is missing; `varna ensure` writes missing files at login so waybar and mako
  always start; a throwaway `HOME` never reloads the running desktop.
