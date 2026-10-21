# Contributing to varna

Thanks for helping. Themes, tool templates and fixes are all welcome.

## Development setup

```sh
git clone https://github.com/Theyashsawarkar/varna ~/code/varna
cd ~/code/varna
ruff check .
python -m unittest discover -s tests -v
HOME=$(mktemp -d) bin/varna apply nord      # renders everything; a throwaway HOME never reloads your desktop
```

## Adding a theme

A file in `themes/<id>.toml` with all 26 palette colours (`varna show vayu`
lists them) and, if the theme has one, its light/dark twin in `[meta]`.
Credit the palette's source in a comment. The tests render every theme
through every template.

## Adding a tool

1. A template in `varna/templates/` using `{{names}}` (README, "Theming any file").
2. An entry in `TOOLS` (`varna/core.py`): label, template, output, reload.
3. A reloader in `RELOADERS` if the tool can reload live, and a `HOOKS`
   entry: the line its config must contain.
4. A row in the README's tool table.

## Rules

- **A tool's config stays its own**: varna writes one included file, never
  the tool's config itself.
- **Errors, not silent colours**: an unknown name in a template fails.
- **Never touch the running desktop from a test**: reloads only happen when
  `HOME` is the real home (`core.live_home`).
- **Standard library only.**
- Every change gets a `CHANGELOG.md` entry; releases are tags `vX.Y.Z` with
  `VERSION` bumped. The website is generated: `python3 scripts/build-site.py`
  after changing the README, CHANGELOG or ADRs.

## Pull requests

Describe what and why, and tick the template's checklist. By contributing
you agree your work is released under the [MIT License](LICENSE).
