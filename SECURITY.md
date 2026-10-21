# Security policy

## Supported versions

Only the latest release of varna gets fixes.

## Reporting a vulnerability

Please **don't open a public issue**. Report it privately through
[GitHub's security advisories](https://github.com/Theyashsawarkar/varna/security/advisories/new),
with what an attacker could do and how to reproduce it. You'll get a reply
within a week.

## What varna does

varna runs as your user. It reads theme files and writes small files under
`~/.local/state/varna` (and `~/.config/waybar/varna.css`, and the GTK links
when you turn that on), then sends reload signals to your own running tools.
A template you add with `varna template add` can write anywhere you can:
only add templates you trust. varna makes no network requests.
