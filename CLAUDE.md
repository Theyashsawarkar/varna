# varna -- notes for agents

One theme for every tool: themes (TOML) rendered through one template per
tool into files the tools' configs include, then reloaded live. Its own
repo, pulled into Vayu (github.com/Theyashsawarkar/vayu, whose CLAUDE.md
"Plugins" rules apply); it must work without Vayu. vinyasa (the settings
app) drives it through `varna.core`.

- `bin/varna` entry; `varna/core.py` themes, config, resolve, render, apply,
  reloaders, hooks; `varna/cli.py` commands; `varna/templates/` one per tool;
  `themes/` the shipped themes.
- **Never reload the user's running desktop from a test**: use a throwaway
  HOME (`HOME=$(mktemp -d) bin/varna apply ...`); `core.live_home()` blocks
  reloads there. Don't run `varna apply/mode/set` against the real HOME
  unless the user asked.
- A template may only use names every theme resolves (the 26 palette keys,
  roles, ui values) or `{{extra|fallback}}`; the tests render every theme
  through every template.
- Standard library only. `ruff check .` and `python -m unittest discover -s tests` must pass.
- Every change: a CHANGELOG.md entry; releases are tags with `VERSION` bumped.
- The website (docs/, GitHub Pages) is generated: after changing README.md, CHANGELOG.md or docs/adr/, run `python3 scripts/build-site.py` and commit docs/ (CI checks it). A significant design decision gets a new ADR in docs/adr/ (next number; supersede, never rewrite).
