# Changelog

Newest first. Releases are tags (`vX.Y.Z`) with `VERSION` in `varna/__init__.py`.

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
