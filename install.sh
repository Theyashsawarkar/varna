#!/usr/bin/env bash
# varna's installer: clones varna into ~/.local/share/varna (its newest
# release) and links ~/.local/bin/varna. No root.
#
#   curl -fsSL https://raw.githubusercontent.com/Theyashsawarkar/varna/main/install.sh | bash
set -euo pipefail
dest="${XDG_DATA_HOME:-$HOME/.local/share}/varna"
bin="$HOME/.local/bin"
command -v git >/dev/null || { echo "varna needs git" >&2; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null ||
  { echo "varna needs Python 3.11 or newer" >&2; exit 1; }
if [ -d "$dest/.git" ]; then
  git -C "$dest" fetch -q --tags origin
else
  git clone -q https://github.com/Theyashsawarkar/varna "$dest"
fi
latest=$(git -C "$dest" tag -l 'v*' --sort=-v:refname | head -1)
[ -n "$latest" ] && git -C "$dest" -c advice.detachedHead=false checkout -q "$latest"
mkdir -p "$bin"
ln -sfn "$dest/bin/varna" "$bin/varna"
echo "varna ${latest:-(main)} installed: $bin/varna"
case ":$PATH:" in *":$bin:"*) ;; *) echo "add $bin to your PATH" ;; esac
"$bin/varna" ensure >/dev/null 2>&1 || true
echo "next: varna doctor (what each tool's config needs), then varna apply <theme>"
