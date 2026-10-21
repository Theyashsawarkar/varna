"""varna's engine: themes, the config, rendering a tool's colours, applying.

A theme is a TOML file: [meta], [palette] (named colours), [roles] (what
the accent is, what a warning is...), [ui] (fonts, radius, opacity, gaps)
and optional [tools.<tool>] extras. ~/.config/varna/varna.toml picks the
desktop's theme and lets any tool pick its own. `apply` renders each tool's
template with its theme and writes the result to ~/.local/state/varna/,
where the tool's own config includes it, then reloads the tool.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import time
import tomllib

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.abspath(__file__))
BUILTIN_THEMES = os.path.join(os.path.dirname(HERE), "themes")
TEMPLATES = os.path.join(HERE, "templates")
CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config"), "varna")
USER_THEMES = os.path.join(CONFIG_DIR, "themes")
CONFIG = os.path.join(CONFIG_DIR, "varna.toml")
STATE = os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local", "state"), "varna")
RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"


class VarnaError(Exception):
    pass


# The colours every template may rely on (Catppuccin's names, the de facto
# standard): a theme maps its own colours onto these.
PALETTE_KEYS = ["crust", "mantle", "base", "surface0", "surface1", "surface2", "overlay0", "overlay1", "overlay2",
                "subtext0", "subtext1", "text", "rosewater", "flamingo", "pink", "mauve", "red", "maroon", "peach",
                "yellow", "green", "teal", "sky", "sapphire", "blue", "lavender"]
# What things are for. A theme sets any of them (a palette name or a hex);
# the rest default to these.
ROLE_DEFAULTS = {
    "accent": "mauve",            # the active workspace, tmux session and window, selections
    "accent2": "pink",            # the second highlight: popup and pane borders
    "border": "accent",           # the focused window's border
    "border_inactive": "surface1",
    "urgent": "red",
    "ink": "crust",               # text on a coloured capsule
    "fg": "text",
    "bg": "base",
    "muted": "overlay0",
    "line": "surface1",           # quiet separators
    "selection": "surface1",
    "match": "yellow",            # search matches
    "mark": "pink",
    "ok": "green", "warn": "yellow", "error": "red", "info": "blue",
}
UI_DEFAULTS = {"font": "Sans", "mono": "JetBrainsMono Nerd Font", "size": 11, "mono_size": 12,
               "radius": 12, "opacity": 0.85, "gaps": 4, "border_width": 2}
HEX = re.compile(r"^#?([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$")

# Every tool varna themes: its template, where the result goes, how it reloads.
# kind "include": the tool's config includes the output (sway, tmux...).
TOOLS = {
    "sway": dict(label="Sway (window borders, gaps)", template="sway.conf", out="sway.conf", reload="sway"),
    "waybar": dict(label="Waybar", template="waybar.css", out="~/.config/waybar/varna.css", reload="waybar"),
    "tmux": dict(label="tmux", template="tmux.conf", out="tmux.conf", reload="tmux"),
    "kitty": dict(label="kitty", template="kitty.conf", out="kitty.conf", reload="kitty"),
    "mako": dict(label="Notifications (mako)", template="mako.conf", out="mako.conf", reload="mako"),
    "vyom": dict(label="Vyom panels and tools", template="vyom.css", out="vyom.css", reload="vyom"),
    "nvim": dict(label="Neovim", template="nvim.lua", out="nvim.lua", reload="nvim"),
    "prompt": dict(label="zsh prompt (powerlevel10k)", template="p10k.zsh", out="p10k.zsh", reload=None),
    "fzf": dict(label="fzf", template="fzf.sh", out="fzf.sh", reload=None),
    "lazygit": dict(label="lazygit", template="lazygit.yml", out="lazygit.yml", reload=None),
    "swaylock": dict(label="Lock screen (swaylock)", template="swaylock.conf", out="swaylock.args", reload=None, header=False),
    "gtk": dict(label="GTK apps", template="gtk.css", out="gtk.css", reload="gtk", optional=True),
    "apps": dict(label="Vayu's tools (vesha, nāda, vinyasa…)", template=None, out="palette.json", reload=None),
}


# Where each tool picks varna up: (file, text it must contain, the line to add).
HOOKS = {
    "sway": ("~/.config/sway/config", "varna/sway", "include ~/.local/state/varna/sway*.conf   (at the end)"),
    "waybar": ("~/.config/waybar/style.css", "varna.css", '@import "varna.css";   (at the top of style.css)'),
    "tmux": ("~/.config/tmux/tmux.conf", "varna/tmux.conf", "source-file -q ~/.local/state/varna/tmux.conf   (at the end)"),
    "kitty": ("~/.config/kitty/kitty.conf", "varna/kitty.conf", "include ~/.local/state/varna/kitty.conf   (at the end)"),
    "mako": ("~/.config/mako/config", "varna/mako.conf", "include=~/.local/state/varna/mako.conf   (before the first [section])"),
    "vyom": ("~/.config/vyom/config.toml", "varna/vyom.css", 'css = ["~/.local/state/varna/vyom.css"]   (under [vyom])'),
    "nvim": ("~/.config/nvim/lua/varna.lua", "varna", "lua/varna.lua and catppuccin's color_overrides (see varna's README)"),
    "prompt": ("~/.zshrc", "varna/p10k.zsh", "[ -f ~/.local/state/varna/p10k.zsh ] && source ~/.local/state/varna/p10k.zsh   (after ~/.p10k.zsh)"),
    "fzf": ("~/.zshrc", "varna/fzf.sh", "[ -f ~/.local/state/varna/fzf.sh ] && source ~/.local/state/varna/fzf.sh"),
    "lazygit": ("~/.zshrc", "varna/lazygit.yml",
                'export LG_CONFIG_FILE="$HOME/.config/lazygit/config.yml,$HOME/.local/state/varna/lazygit.yml"'),
    "swaylock": ("~/.config/sway/config", "swaylock.args|vayu-lock", "swaylock $(cat ~/.local/state/varna/swaylock.args)   (or Vayu's vayu-lock)"),
}


def hook_ok(tool):
    """True / False if varna can tell whether the tool includes its file; None if it can't."""
    if tool not in HOOKS:
        return None
    path, needle, _ = HOOKS[tool]
    path = os.path.expanduser(path)
    try:
        with open(path, errors="ignore") as f:
            text = f.read()
        return any(n in text for n in needle.split("|"))
    except OSError:
        return False


# ===================================================================== colours
def hex_rgb(value):
    m = HEX.match(str(value).strip())
    if not m:
        raise VarnaError(f"not a colour: {value!r}")
    h = m.group(1)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def is_hex(value):
    return isinstance(value, str) and bool(HEX.match(value.strip()))


def norm_hex(value):
    m = HEX.match(value.strip())
    return "#" + m.group(1).lower() + (m.group(2) or "").lower()


def mix(a, b, t):
    """a blended toward b by t (0..1), as #rrggbb."""
    ra, rb = hex_rgb(a), hex_rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ra, rb, strict=True))


def luminance(value):
    r, g, b = (c / 255 for c in hex_rgb(value))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


# ===================================================================== themes
def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not s:
        raise VarnaError("a theme needs a name")
    return s


def theme_paths():
    """{id: path}; a theme of yours with a shipped theme's id replaces it."""
    out = {}
    for d in (BUILTIN_THEMES, USER_THEMES):
        for p in sorted(glob.glob(os.path.join(d, "*.toml"))):
            out[os.path.splitext(os.path.basename(p))[0]] = p
    return out


def load_theme(tid):
    paths = theme_paths()
    if tid not in paths:
        near = [t for t in paths if tid.lower() in t]
        raise VarnaError(f"no theme called {tid}" + (f" (did you mean {near[0]}?)" if near else "") + ": varna list shows them")
    try:
        with open(paths[tid], "rb") as f:
            t = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise VarnaError(f"{paths[tid]}: {e}") from None
    t.setdefault("meta", {})
    t["meta"].setdefault("name", tid)
    t["meta"].setdefault("variant", "dark")
    t["id"] = tid
    t["path"] = paths[tid]
    t["user"] = paths[tid].startswith(USER_THEMES)
    check_theme(t)
    return t


def check_theme(t):
    pal = t.get("palette") or {}
    missing = [k for k in PALETTE_KEYS if k not in pal]
    if missing:
        raise VarnaError(f"theme {t['id']} is missing colours: {', '.join(missing)}")
    for k, v in pal.items():
        if not is_hex(v):
            raise VarnaError(f"theme {t['id']}: palette.{k} = {v!r} isn't a #rrggbb colour")


def themes():
    """Every theme, loadable or not: [(id, theme or VarnaError)]."""
    out = []
    for tid in theme_paths():
        try:
            out.append((tid, load_theme(tid)))
        except VarnaError as e:
            out.append((tid, e))
    return out


# ===================================================================== config
def load_config():
    try:
        with open(CONFIG, "rb") as f:
            conf = tomllib.load(f)
    except FileNotFoundError:
        conf = {}
    except tomllib.TOMLDecodeError as e:
        raise VarnaError(f"{CONFIG}: {e}") from None
    conf.setdefault("theme", "vayu")
    conf.setdefault("tools", {})
    conf.setdefault("ui", {})
    conf.setdefault("disabled", [])
    conf.setdefault("template", [])
    return conf


def _toml_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_toml_value(x)}" for k, x in v.items()) + " }"
    raise VarnaError(f"can't write {v!r} to TOML")


def save_config(conf):
    """Writes varna.toml (a small, fixed shape: no comments survive)."""
    lines = ["# varna: the desktop's theme. Written by `varna` and vinyasa; edit freely.", ""]
    for k in ("theme", "accent", "mode", "gtk"):
        if k in conf and conf[k] not in (None, ""):
            lines.append(f"{k} = {_toml_value(conf[k])}")
    if conf.get("disabled"):
        lines.append(f"disabled = {_toml_value(conf['disabled'])}")
    for section in ("ui", "tools"):
        if conf.get(section):
            lines += ["", f"[{section}]"]
            lines += [f"{k} = {_toml_value(v)}" for k, v in conf[section].items()]
    for t in conf.get("template", []):
        lines += ["", "[[template]]"] + [f"{k} = {_toml_value(v)}" for k, v in t.items()]
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = CONFIG + ".tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, CONFIG)


# ===================================================================== resolve
def resolve(conf, tool=None):
    """The colours and values a tool's template sees: {name: value}, plus the
    theme that supplied them. A tool's own pick (a theme id, or a table with
    theme/accent/opacity...) overrides the desktop's."""
    pick = conf.get("tools", {}).get(tool) if tool else None
    if isinstance(pick, str):
        pick = {"theme": pick}
    pick = pick or {}
    tid = pick.get("theme") or conf.get("theme") or "vayu"
    t = load_theme(tid)
    pal = {k: norm_hex(v) for k, v in t["palette"].items()}
    ctx = dict(pal)
    raw_roles = dict(ROLE_DEFAULTS)
    raw_roles.update(t.get("roles") or {})
    if not pick.get("theme") and conf.get("accent"):     # the desktop's accent override
        raw_roles["accent"] = conf["accent"]
    if pick.get("accent"):
        raw_roles["accent"] = pick["accent"]
    # roles may name a palette colour or another role; resolve until a hex
    roles = {}
    for name in raw_roles:
        v, seen = raw_roles[name], set()
        while not is_hex(v):
            if v in seen or (v not in pal and v not in raw_roles):
                raise VarnaError(f"theme {tid}: role {name} = {raw_roles[name]!r} isn't a colour or a palette name")
            seen.add(v)
            v = pal.get(v) or raw_roles[v]
        roles[name] = norm_hex(v)
    ctx.update(roles)
    extras = (t.get("tools") or {}).get(tool) or {} if tool else {}
    for k, v in extras.items():
        ctx[k] = norm_hex(v) if is_hex(v) else ctx.get(v, v)
    ui = dict(UI_DEFAULTS, font=desktop_font())
    ui.update(t.get("ui") or {})
    ui.update(conf.get("ui") or {})
    ui.update({k: v for k, v in pick.items() if k in UI_DEFAULTS})
    ctx.update(ui)
    ctx["variant"] = t["meta"]["variant"]
    ctx["dark"] = "true" if t["meta"]["variant"] == "dark" else "false"
    ctx["theme"] = tid
    ctx["theme_name"] = t["meta"]["name"]
    return ctx, t


_font = []


def desktop_font():
    """The interface font the desktop uses now (GTK's font-name), so varna
    never imposes one you didn't pick; "Sans" without gsettings."""
    if not _font:
        fam = "Sans"
        try:
            out = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "font-name"],
                                 capture_output=True, text=True, timeout=2).stdout.strip().strip("'")
            fam = re.sub(r"\s+\d+(\.\d+)?$", "", out) or fam
        except (OSError, subprocess.TimeoutExpired):
            pass
        _font.append(fam)
    return _font[0]


# ===================================================================== render
EXPR = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def flags():
    """Facts a template line can depend on: `?swayfx corner_radius 12` is
    kept only on SwayFX."""
    out = {}
    try:
        v = subprocess.run(["sway", "--version"], capture_output=True, text=True, timeout=3).stdout.lower()
        out["swayfx"] = "swayfx" in v
    except (OSError, subprocess.TimeoutExpired):
        out["swayfx"] = False
    return out


COND = re.compile(r"^\?(!?)([a-z_]+) ", re.M)


def conditions(text, facts):
    keep = []
    for line in text.splitlines(keepends=True):
        m = COND.match(line)
        if m:
            want = not m.group(1)
            if bool(facts.get(m.group(2))) != want:
                continue
            line = line[m.end():]
        keep.append(line)
    return "".join(keep)


def render(text, ctx, where="template"):
    """{{name}}, {{name|fallback}}, {{name:filter}}. Filters: hex (default),
    a=0.35 (#rrggbbaa), rgb (r, g, b), semi (r;g;b), rgba=0.4, alpha=0.4 (GTK alpha()),
    bare (rrggbb), upper, mix=other:0.3. Unknown names are an error, so a
    typo never ships silently."""
    def one(m):
        expr = m.group(1)
        name, _, flt = expr.partition(":")
        value = None
        for cand in name.split("|"):
            cand = cand.strip()
            if cand in ctx:
                value = ctx[cand]
                break
            if is_hex(cand):
                value = norm_hex(cand)
                break
        if value is None:
            raise VarnaError(f"{where}: unknown name in {{{{{expr}}}}}")
        flt = flt.strip()
        if not is_hex(str(value)):
            if flt:
                raise VarnaError(f"{where}: {name} isn't a colour, so :{flt} can't apply")
            return str(value)
        h = norm_hex(value)[:7]
        if not flt or flt == "hex":
            return h
        if flt == "upper":
            return h.upper()
        if flt == "bare":
            return h[1:]
        if flt == "rgb":
            return ", ".join(str(c) for c in hex_rgb(h))
        if flt == "semi":   # for terminal colour codes: \e[38;2;{{red:semi}}m
            return ";".join(str(c) for c in hex_rgb(h))
        key, _, arg = flt.partition("=")
        if key == "a":
            return h + f"{round(float(arg) * 255):02x}"
        if key == "rgba":
            return f"rgba({', '.join(str(c) for c in hex_rgb(h))}, {float(arg):g})"
        if key == "alpha":
            return f"alpha({h}, {float(arg):g})"
        if key == "mix":
            other, _, t = arg.partition(":")
            return mix(h, ctx.get(other, other), float(t))
        raise VarnaError(f"{where}: unknown filter :{flt}")
    return EXPR.sub(one, text)


def palette_json(ctx, t):
    """What our own tools read: every colour, the roles and the ui values."""
    return {"theme": t["id"], "name": t["meta"]["name"], "variant": t["meta"]["variant"],
            "colors": {k: v for k, v in ctx.items() if is_hex(str(v))},
            "ui": {k: ctx[k] for k in UI_DEFAULTS}, "written": int(time.time())}


_facts = {}


def FACTS():
    if not _facts:
        _facts.update(flags())
    return _facts


# ===================================================================== apply
def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".varna-tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def tool_enabled(conf, tool):
    if tool in conf.get("disabled", []):
        return False
    if TOOLS[tool].get("optional"):
        return bool(conf.get(tool) if tool != "gtk" else conf.get("gtk"))
    return True


def out_path(tool):
    out = TOOLS[tool]["out"]
    return os.path.expanduser(out) if out.startswith("~") else os.path.join(STATE, out)


def render_tool(conf, tool):
    """(output path, text) for one built-in tool, without writing."""
    spec = TOOLS[tool]
    ctx, t = resolve(conf, tool)
    out = out_path(tool)
    if spec["template"] is None:
        # Vayu's own tools: the desktop's palette, plus each tool's own pick
        data = palette_json(ctx, t)
        data["tools"] = {}
        for name in conf.get("tools", {}):
            if name not in TOOLS:
                c2, t2 = resolve(conf, name)
                data["tools"][name] = palette_json(c2, t2)
        return out, json.dumps(data, indent=2) + "\n"
    with open(os.path.join(TEMPLATES, spec["template"])) as f:
        src = f.read()
    header = None if spec.get("header") is False else \
        {".css": "/* {} */", ".lua": "-- {}", ".json": None}.get(os.path.splitext(spec["out"])[1], "# {}")
    note = f"generated by varna from theme {t['id']}: don't edit, it's rewritten on every apply"
    text = render(conditions(src, FACTS()), ctx, f"{tool} template")
    return out, (header.format(note) + "\n" if header else "") + text


def render_user(conf, entry):
    """A template of yours ([[template]] in varna.toml): src rendered to dst."""
    src = os.path.expanduser(entry["src"])
    dst = os.path.expanduser(entry["dst"])
    ctx, _ = resolve(conf, entry.get("tool"))
    with open(src) as f:
        return dst, render(f.read(), ctx, src.replace(HOME, "~"))


def apply(conf=None, only=None, reload=True, on_step=None):
    """Renders and writes every enabled tool (or `only` those), then reloads
    them. Returns [(name, "ok"|"skipped"|"failed", detail)]. A tool that
    fails never stops the others."""
    conf = conf or load_config()
    if reload and not live_home():
        reload = False   # a throwaway HOME must never restyle the real, running desktop
    results = []
    names = [n for n in TOOLS if (only is None or n in only)]
    rendered = {}
    for name in names:
        if not tool_enabled(conf, name):
            if name == "gtk":
                remove_gtk()
            results.append((name, "skipped", "turned off"))
            continue
        try:
            path, text = render_tool(conf, name)
            write(path, text)
            rendered[name] = path
        except (VarnaError, OSError) as e:
            results.append((name, "failed", str(e)))
            if on_step:
                on_step(name, "failed", str(e))
    for entry in conf.get("template", []):
        label = entry.get("name") or os.path.basename(entry.get("dst", "?"))
        if only is not None and entry.get("tool") not in only and label not in only:
            continue
        try:
            dst, text = render_user(conf, entry)
            write(dst, text)
            rendered.setdefault(entry.get("tool") or label, dst)
        except (VarnaError, OSError, KeyError) as e:
            results.append((label, "failed", str(e)))
    for name, path in rendered.items():
        detail = path.replace(HOME, "~")
        if reload and name in TOOLS and TOOLS[name]["reload"]:
            try:
                detail = RELOADERS[TOOLS[name]["reload"]](conf) or detail
            except Exception as e:   # a tool that isn't running is fine; anything else is reported
                results.append((name, "failed", f"written, but reloading failed: {e}"))
                continue
        results.append((name, "ok", detail))
        if on_step:
            on_step(name, "ok", detail)
    if reload and (only is None or "apps" in only):
        try:
            color_scheme(load_theme(conf.get("theme") or "vayu")["meta"]["variant"])
        except (VarnaError, OSError, subprocess.SubprocessError):
            pass
    order = {n: i for i, n in enumerate(TOOLS)}
    return sorted(results, key=lambda r: order.get(r[0], len(order)))


# ===================================================================== reload
def live_home():
    """Whether HOME is this user's real home: only then do running tools get
    reloaded (tests and previews use a throwaway HOME)."""
    import pwd
    try:
        return os.path.realpath(HOME) == os.path.realpath(pwd.getpwuid(os.getuid()).pw_dir)
    except KeyError:
        return False


def _run(cmd, timeout=5):
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout).returncode


def _pids(name):
    out = []
    for pid in os.listdir("/proc"):
        if pid.isdigit():
            try:
                with open(f"/proc/{pid}/comm") as f:
                    if f.read().strip() == name:
                        out.append(int(pid))
            except OSError:
                pass
    return out


def _signal(name, sig):
    n = 0
    for pid in _pids(name):
        try:
            os.kill(pid, sig)
            n += 1
        except OSError:
            pass
    return n


def reload_sway(conf):
    if not os.environ.get("SWAYSOCK") and not glob.glob(os.path.join(RUNTIME, "sway-ipc.*.sock")):
        return "sway isn't running"
    sock = os.environ.get("SWAYSOCK") or sorted(glob.glob(os.path.join(RUNTIME, "sway-ipc.*.sock")))[-1]
    _run(["swaymsg", "-s", sock, "reload"])
    return "reloaded"


def reload_waybar(conf):
    import signal
    return "reloaded" if _signal("waybar", signal.SIGUSR2) else "not running"


def reload_tmux(conf):
    socks = glob.glob(f"/tmp/tmux-{os.getuid()}/*")
    if os.environ.get("TMUX_TMPDIR"):
        socks += glob.glob(os.path.join(os.environ["TMUX_TMPDIR"], f"tmux-{os.getuid()}", "*"))
    done = 0
    for s in socks:
        if _run(["tmux", "-S", s, "source-file", "-q", os.path.join(STATE, "tmux.conf")], timeout=3) == 0:
            _run(["tmux", "-S", s, "refresh-client", "-S"], timeout=3)
            done += 1
    return f"{done} server{'s' if done != 1 else ''}" if done else "not running"


def reload_kitty(conf):
    import signal
    n = _signal("kitty", signal.SIGUSR1)
    return f"{n} window{'s' if n != 1 else ''}" if n else "not running"


def reload_mako(conf):
    return "reloaded" if shutil.which("makoctl") and _run(["makoctl", "reload"]) == 0 else "not running"


def reload_vyom(conf):
    return "reloaded" if shutil.which("vyom") and _run(["vyom", "reload"]) == 0 else "not running"


def reload_nvim(conf):
    socks = glob.glob(os.path.join(RUNTIME, "nvim.*")) + glob.glob(f"/tmp/nvim.{os.environ.get('USER', '')}/*/nvim.*")
    done = 0
    expr = "luaeval('pcall(function() require(\"varna\").reload() end)')"
    for s in socks:
        if shutil.which("nvim") and _run(["nvim", "--server", s, "--remote-expr", expr], timeout=4) == 0:
            done += 1
    return f"{done} running" if done else "next start"


def reload_gtk(conf):
    ctx, _ = resolve(conf, "gtk")
    scheme = "prefer-dark" if ctx["variant"] == "dark" else "prefer-light"
    if shutil.which("gsettings"):
        _run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", scheme])
    for v in ("gtk-3.0", "gtk-4.0"):
        link = os.path.join(HOME, ".config", v, "gtk.css")
        target = os.path.join(STATE, "gtk.css")
        if os.path.islink(link) or not os.path.exists(link):
            if os.path.islink(link):
                os.remove(link)
            os.makedirs(os.path.dirname(link), exist_ok=True)
            os.symlink(target, link)
    return "new windows (and apps that follow the dark/light signal)"


def remove_gtk():
    for v in ("gtk-3.0", "gtk-4.0"):
        link = os.path.join(HOME, ".config", v, "gtk.css")
        if os.path.islink(link) and os.readlink(link).startswith(STATE):
            os.remove(link)


RELOADERS = {"sway": reload_sway, "waybar": reload_waybar, "tmux": reload_tmux, "kitty": reload_kitty,
             "mako": reload_mako, "vyom": reload_vyom, "nvim": reload_nvim, "gtk": reload_gtk}


# ===================================================================== editing themes
def write_theme(tid, theme):
    """Saves a theme of yours to ~/.config/varna/themes/<id>.toml."""
    check_theme({"id": tid, **theme})
    lines = [f"# {theme.get('meta', {}).get('name', tid)}: a varna theme", ""]
    for section in ("meta", "palette", "roles", "ui"):
        if theme.get(section):
            lines.append(f"[{section}]")
            lines += [f"{k} = {_toml_value(v)}" for k, v in theme[section].items()]
            lines.append("")
    for tool, extras in (theme.get("tools") or {}).items():
        lines.append(f"[tools.{tool}]")
        lines += [f"{k} = {_toml_value(v)}" for k, v in extras.items()]
        lines.append("")
    os.makedirs(USER_THEMES, exist_ok=True)
    path = os.path.join(USER_THEMES, f"{tid}.toml")
    write(path, "\n".join(lines))
    return path


def copy_theme(src_id, name):
    t = load_theme(src_id)
    tid = slug(name)
    if tid in theme_paths() and not theme_paths()[tid].startswith(USER_THEMES):
        tid = tid + "-custom"
    new = {k: t[k] for k in ("palette", "roles", "ui", "tools") if t.get(k)}
    new["meta"] = dict(t["meta"], name=name)
    new["meta"].pop("light", None)
    new["meta"].pop("dark", None)
    return tid, write_theme(tid, new)


def delete_theme(tid):
    path = theme_paths().get(tid)
    if not path or not path.startswith(USER_THEMES):
        raise VarnaError(f"{tid} is a shipped theme: only your own themes can be deleted")
    os.remove(path)


# ===================================================================== settings helpers
def set_value(key, value):
    """varna set <key> <value>: theme, accent, mode, gtk, or ui.<name>."""
    conf = load_config()
    if key == "theme":
        load_theme(value)
        conf["theme"] = value
    elif key == "accent":
        conf["accent"] = value if value not in ("", "default", "theme") else None
        resolve(conf)   # validates: a palette name or a hex
    elif key == "gtk":
        conf["gtk"] = value in ("on", "true", "yes", "1")
    elif key.startswith("ui.") and key[3:] in UI_DEFAULTS:
        k = key[3:]
        if value in ("", "default"):
            conf["ui"].pop(k, None)
        else:
            conf["ui"][k] = type(UI_DEFAULTS[k])(value) if not isinstance(UI_DEFAULTS[k], str) else value
    else:
        raise VarnaError(f"unknown setting {key}: theme, accent, gtk, ui.{'/ui.'.join(UI_DEFAULTS)}")
    save_config(conf)
    return conf


def set_tool(tool, value):
    """varna tool <tool> <theme|follow>."""
    conf = load_config()
    if tool not in TOOLS and tool not in conf.get("tools", {}) and not re.match(r"^[a-z0-9_-]+$", tool):
        raise VarnaError(f"unknown tool {tool}")
    if value in ("follow", "default", "desktop", ""):
        conf["tools"].pop(tool, None)
    else:
        load_theme(value)
        conf["tools"][tool] = value
    save_config(conf)
    return conf


def ensure():
    """Writes every enabled tool's file that's missing, reloading nothing:
    run at login, before the tools start, so none of them fails on a missing
    include. Returns the tools written."""
    conf = load_config()
    missing = [n for n in TOOLS if tool_enabled(conf, n) and not os.path.exists(out_path(n))]
    missing += [e.get("tool") or os.path.basename(e["dst"]) for e in conf.get("template", [])
                if not os.path.exists(os.path.expanduser(e["dst"]))]
    if not missing:
        return []
    results = apply(conf, only=set(missing), reload=False)
    return [r[0] for r in results if r[1] == "ok"]


def twin(t, variant):
    """The theme's light or dark twin id (meta.light / meta.dark), or None."""
    if t["meta"]["variant"] == variant:
        return t["id"]
    other = t["meta"].get(variant)
    return other if other in theme_paths() else None


def set_mode(mode):
    """varna mode dark|light|toggle: switch to the theme's twin. Returns the theme id."""
    conf = load_config()
    t = load_theme(conf["theme"])
    if mode == "toggle":
        mode = "light" if t["meta"]["variant"] == "dark" else "dark"
    if mode not in ("dark", "light"):
        raise VarnaError("varna mode dark|light|toggle")
    tid = twin(t, mode)
    if not tid:
        raise VarnaError(f"{t['meta']['name']} has no {mode} twin: pick a {mode} theme (varna list)")
    conf["theme"] = tid
    save_config(conf)
    return tid


def color_scheme(variant):
    """Tells apps that follow the desktop (browsers, GTK, portals) dark or light."""
    if shutil.which("gsettings"):
        _run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme",
              "prefer-dark" if variant == "dark" else "prefer-light"])

