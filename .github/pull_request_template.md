## What and why

<!-- What this changes and why. -->

## Checklist

- [ ] `ruff check .` and `python -m unittest discover -s tests` pass (every theme renders through every template)
- [ ] Tried with a throwaway home (`HOME=$(mktemp -d) bin/varna apply <theme>`), never by restyling my own desktop from a test
- [ ] A new tool: template, `TOOLS`, `HOOKS`, a reloader if it can reload, and a README row
- [ ] A new theme: all 26 colours, the source credited, its twin linked if it has one
- [ ] A `CHANGELOG.md` entry; the website rebuilt if README, CHANGELOG or ADRs changed
