"""varna's commands. `varna help` lists them."""
import json
import os
import subprocess
import sys
import time

from . import VERSION, core, ui
from .core import VarnaError
from .ui import c

COMMANDS = {
    "status": dict(group="Theme", aliases=[], args="",
                   summary="The desktop's theme, its accent, and each tool's pick",
                   examples=["varna", "varna status"]),
    "list": dict(group="Theme", aliases=["ls"], args="[--json]",
                 summary="Every theme, with its colours", examples=["varna list"]),
    "apply": dict(group="Theme", aliases=["use"], args="[theme] [--only tool,...] [--no-reload]",
                  summary="Switch the desktop's theme (or re-apply the current one) and reload every tool",
                  description="Renders every tool's colours from the theme, writes them where each tool's config "
                              "includes them, and reloads the tools that are running. A tool with its own theme (varna "
                              "tool) keeps it. A failing tool never stops the others.",
                  examples=["varna apply rose-pine", "varna apply", "varna apply --only tmux,kitty"]),
    "mode": dict(group="Theme", aliases=[], args="dark|light|toggle",
                 summary="Switch to the theme's dark or light twin (Catppuccin Mocha ⇄ Latte, Rosé Pine ⇄ Dawn)",
                 examples=["varna mode toggle", "varna mode light"]),
    "show": dict(group="Theme", aliases=[], args="[theme] [--tool name]",
                 summary="A theme's palette and roles, as colour swatches", examples=["varna show nord", "varna show --tool tmux"]),
    "set": dict(group="Theme", aliases=[], args="<setting> <value>",
                summary="Change one setting: accent, gtk, ui.opacity, ui.gaps, ui.radius, ui.font...",
                description="accent takes a palette name (mauve, blue...) or a #hex, or `default` for the theme's own. "
                            "gtk on/off themes GTK apps too. ui.* values: font, mono, size, mono_size, radius, opacity, "
                            "gaps, border_width (`default` drops yours). Applies right away.",
                examples=["varna set accent blue", "varna set ui.gaps 8", "varna set gtk on"]),
    "tool": dict(group="Tools", aliases=[], args="<tool> [theme|follow]",
                 summary="Give one tool its own theme (or make it follow the desktop again)",
                 examples=["varna tool nvim tokyo-night", "varna tool nvim follow"]),
    "tools": dict(group="Tools", aliases=[], args="",
                  summary="Every tool varna themes, its theme, and whether its config includes varna",
                  examples=["varna tools"]),
    "new": dict(group="Your themes", aliases=["copy"], args="<name> [--from theme]",
                summary="Make a theme of your own, starting from another", examples=["varna new 'Rose Dusk' --from vayu"]),
    "edit": dict(group="Your themes", aliases=[], args="<theme>",
                 summary="Open a theme of yours in $EDITOR (a shipped one is copied first), then apply it if it's in use",
                 examples=["varna edit rose-dusk"]),
    "delete": dict(group="Your themes", aliases=["rm"], args="<theme>",
                   summary="Delete a theme of yours", examples=["varna delete rose-dusk"]),
    "template": dict(group="Your themes", aliases=[], args="add <src> <dst> [--tool name] | remove <dst> | list",
                     summary="Theme any file: render a template of yours on every apply",
                     description="A template is any file with {{accent}}, {{base:a=0.5}}, {{text:rgb}}... in it. varna "
                                 "renders it to dst on every apply, with the desktop's theme or the tool's own.",
                     examples=["varna template add ~/.config/waybar/config.varna ~/.config/waybar/config --tool waybar"]),
    "palette": dict(group="For scripts", aliases=[], args="[--tool name]",
                    summary="The resolved colours as JSON (what Vayu's own tools read)", examples=["varna palette --tool nvim"]),
    "ensure": dict(group="For scripts", aliases=[], args="",
                   summary="Write any missing tool file, reloading nothing (run at login, before the tools start)",
                   examples=["varna ensure"]),
    "doctor": dict(group="For scripts", aliases=["check"], args="",
                   summary="Check every theme loads and every tool's config includes varna", examples=["varna doctor"]),
    "help": dict(group="Help", aliases=[], args="[command]", summary="This overview, or one command in detail",
                 examples=["varna help apply"]),
}
ALIASES = {a: n for n, d in COMMANDS.items() for a in d["aliases"]}


def swatch(h, w=2):
    if not ui.TTY:
        return h
    r, g, b = core.hex_rgb(h)
    return f"\033[48;2;{r};{g};{b}m{' ' * w}\033[0m"


def strip_swatches(theme, keys=("base", "surface0", "text", "red", "peach", "yellow", "green", "teal", "blue", "mauve", "pink")):
    return "".join(swatch(theme["palette"][k]) for k in keys)


class Ctx:
    def __init__(self, args):
        self.flags = {a.split("=")[0] for a in args if a.startswith("--")}
        self.opts = {}
        rest, i = [], 0
        while i < len(args):
            a = args[i]
            if a in ("--only", "--tool", "--from") and i + 1 < len(args):
                self.opts[a[2:]] = args[i + 1]
                i += 2
                continue
            if a.startswith("--") and "=" in a:
                k, v = a[2:].split("=", 1)
                self.opts[k] = v
            elif not a.startswith("-") or a == "-":
                rest.append(a)
            i += 1
        self.args = rest
        self.json = "--json" in self.flags
        self.yes = bool({"-y", "--yes"} & set(args))


# ===================================================================== commands
def cmd_status(ctx):
    conf = core.load_config()
    t = core.load_theme(conf["theme"])
    ui.header("Theme", t["meta"]["name"])
    ui.out(f"  {c('theme', 'dim')}   {c(t['meta']['name'], 'text', bold=True)} {c('(' + t['id'] + ', ' + t['meta']['variant'] + ')', 'dim')}"
           f"   {strip_swatches(t)}")
    ctx_, _ = core.resolve(conf)
    acc = conf.get("accent")
    ui.out(f"  {c('accent', 'dim')}  {swatch(ctx_['accent'])} {ctx_['accent']}" + (c(f"  (yours: {acc})", "dim") if acc else c("  (the theme's)", "dim")))
    if conf.get("ui"):
        ui.out(f"  {c('yours', 'dim')}   " + "  ".join(f"{k} {v}" for k, v in conf["ui"].items()))
    picks = conf.get("tools") or {}
    if picks:
        ui.out()
        for tool, pick in picks.items():
            name = pick if isinstance(pick, str) else pick.get("theme", "the desktop's, adjusted")
            ui.out(f"  {ui.pad(c(tool, 'peach', bold=True), 12)} {c('uses', 'dim')} {name}")
    last = os.path.join(core.STATE, "palette.json")
    if os.path.exists(last):
        ui.out(c(f"\n  applied {time.strftime('%H:%M, %b %d', time.localtime(os.path.getmtime(last)))}", "faint"))
    else:
        ui.warn("never applied yet: varna apply")
    return 0


def cmd_list(ctx):
    conf = core.load_config()
    rows, data = [], []
    for tid, t in core.themes():
        if isinstance(t, VarnaError):
            rows.append([c(tid, "red"), c(str(t), "red"), "", ""])
            continue
        data.append({"id": tid, "name": t["meta"]["name"], "variant": t["meta"]["variant"], "yours": t["user"], "path": t["path"]})
        mark = c("●", "green") if tid == conf["theme"] else " "
        rows.append([f"{mark} {c(tid, 'text', bold=tid == conf['theme'])}", t["meta"]["name"],
                     c(t["meta"]["variant"], "dim") + (c("  yours", "peach") if t["user"] else ""), strip_swatches(t)])
    if ctx.json:
        ui.out(json.dumps(data, indent=2))
        return 0
    ui.table(rows, ["Theme", "Name", "", "Colours"], title="Themes")
    ui.note("varna apply <theme> switches; varna new <name> --from <theme> makes your own")
    return 0


def cmd_apply(ctx):
    conf = core.load_config()
    if ctx.args:
        core.load_theme(ctx.args[0])
        conf["theme"] = ctx.args[0]
        core.save_config(conf)
    only = set(ctx.opts["only"].split(",")) if ctx.opts.get("only") else None
    t0 = time.time()
    t = core.load_theme(conf["theme"])
    ui.header("Applying", t["meta"]["name"])
    results = core.apply(conf, only=only, reload="--no-reload" not in ctx.flags)
    picks = conf.get("tools") or {}
    failed = 0
    for name, state, detail in results:
        label = core.TOOLS[name]["label"] if name in core.TOOLS else name
        own = picks.get(name)
        own = f"  ({own if isinstance(own, str) else 'own'})" if own else ""
        if state == "ok":
            ui.out(f"  {c('✓', 'green')} {ui.pad(label, 46)} {c(detail + own, 'dim')}")
        elif state == "skipped":
            ui.out(f"  {c('·', 'faint')} {ui.pad(c(label, 'dim'), 46)} {c(detail, 'faint')}")
        else:
            failed += 1
            ui.out(f"  {c('✗', 'red')} {ui.pad(label, 46)} {c(detail, 'red')}")
    ok_n = sum(1 for r in results if r[1] == "ok")
    ui.out()
    ui.summary([("Themed", ok_n, "green"), ("Failed", failed, "red")])
    ui.note(f"in {time.time() - t0:.1f}s" + ("  ·  some tools take it on their next start (prompt, fzf, lazygit, lock screen)" if ok_n else ""))
    return 1 if failed else 0


def cmd_mode(ctx):
    if not ctx.args:
        t = core.load_theme(core.load_config()["theme"])
        ui.out(t["meta"]["variant"])
        return 0
    tid = core.set_mode(ctx.args[0])
    ui.ok(f"now {tid}")
    return report(core.apply())


def cmd_show(ctx):
    conf = core.load_config()
    if ctx.args:
        conf = dict(conf, theme=ctx.args[0], accent=None)
    values, t = core.resolve(conf, ctx.opts.get("tool"))
    ui.header(t["meta"]["name"], ctx.opts.get("tool") or t["meta"]["variant"])
    keys = core.PALETTE_KEYS
    for i in range(0, len(keys), 4):
        ui.out("  " + "".join(f"{swatch(values[k], 3)} {ui.pad(c(k, 'sub'), 10)} {ui.pad(c(values[k], 'dim'), 9)}  " for k in keys[i:i + 4]))
    ui.out()
    roles = list(core.ROLE_DEFAULTS)
    for i in range(0, len(roles), 4):
        ui.out("  " + "".join(f"{swatch(values[k], 3)} {ui.pad(c(k, 'text'), 15)} {ui.pad(c(values[k], 'dim'), 9)}  " for k in roles[i:i + 4]))
    ui.out()
    ui.out("  " + "  ".join(f"{c(k, 'dim')} {values[k]}" for k in core.UI_DEFAULTS))
    return 0


def cmd_set(ctx):
    if len(ctx.args) < 2:
        raise VarnaError("varna set <setting> <value>   (varna help set)")
    key, value = ctx.args[0], " ".join(ctx.args[1:])
    conf = core.set_value(key, value)
    ui.ok(f"{key} = {value}")
    return report(core.apply(conf))


def cmd_tool(ctx):
    if not ctx.args:
        return cmd_tools(ctx)
    tool = ctx.args[0]
    if len(ctx.args) == 1:
        conf = core.load_config()
        pick = conf["tools"].get(tool)
        ui.out(f"{tool}: " + (str(pick) if pick else "follows the desktop"))
        return 0
    conf = core.set_tool(tool, ctx.args[1])
    ui.ok(f"{tool} " + ("follows the desktop" if tool not in conf["tools"] else f"uses {ctx.args[1]}"))
    return report(core.apply(conf, only={tool} | ({"apps"} if tool not in core.TOOLS else set())))


def cmd_tools(ctx):
    conf = core.load_config()
    rows = []
    for name, spec in core.TOOLS.items():
        pick = conf["tools"].get(name)
        theme = pick if isinstance(pick, str) else (pick or {}).get("theme") if pick else None
        hook = core.hook_ok(name)
        hk = c("–", "faint") if hook is None else c("✓ included", "green") if hook else c("✗ not included", "yellow")
        on = core.tool_enabled(conf, name)
        rows.append([c(name, "text", bold=True), spec["label"], c(theme, "peach") if theme else c("desktop", "dim"),
                     hk if on else c("off", "dim")])
    for name, pick in conf["tools"].items():
        if name not in core.TOOLS:
            rows.append([c(name, "text", bold=True), c("reads palette.json", "dim"), c(str(pick), "peach"), c("–", "faint")])
    ui.table(rows, ["Tool", "", "Theme", "Config"], title="Tools")
    ui.note("varna tool <tool> <theme> gives one its own theme · varna doctor shows what to add where it's not included")
    return 0


def cmd_new(ctx):
    if not ctx.args:
        raise VarnaError("name it: varna new <name> [--from theme]")
    src = ctx.opts.get("from") or core.load_config()["theme"]
    tid, path = core.copy_theme(src, " ".join(ctx.args))
    ui.ok(f"made {c(tid, 'peach', bold=True)} from {src}: {c(path.replace(core.HOME, '~'), 'sky')}")
    ui.note(f"varna edit {tid} to change it, varna apply {tid} to use it (or edit it in vinyasa)")
    return 0


def cmd_edit(ctx):
    if not ctx.args:
        raise VarnaError("varna edit <theme>")
    tid = ctx.args[0]
    t = core.load_theme(tid)
    if not t["user"]:
        tid, _ = core.copy_theme(tid, t["meta"]["name"])
        ui.note(f"{ctx.args[0]} is a shipped theme: editing your copy, {tid}")
    path = core.theme_paths()[tid]
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    subprocess.run([editor, path])
    core.load_theme(tid)   # still valid?
    conf = core.load_config()
    if conf["theme"] == tid or tid in [p if isinstance(p, str) else p.get("theme") for p in conf["tools"].values()]:
        return report(core.apply(conf))
    ui.ok(f"saved {tid}: varna apply {tid} to use it")
    return 0


def cmd_delete(ctx):
    if not ctx.args:
        raise VarnaError("varna delete <theme>")
    tid = ctx.args[0]
    conf = core.load_config()
    if conf["theme"] == tid:
        raise VarnaError(f"{tid} is the desktop's theme: switch to another first (varna apply <theme>)")
    core.delete_theme(tid)
    for tool, pick in list(conf["tools"].items()):
        if pick == tid:
            conf["tools"].pop(tool)
    core.save_config(conf)
    ui.ok(f"deleted {tid}")
    return 0


def cmd_template(ctx):
    conf = core.load_config()
    what = (ctx.args or ["list"])[0]
    if what == "add":
        if len(ctx.args) < 3:
            raise VarnaError("varna template add <src> <dst> [--tool name]")
        src, dst = ctx.args[1], ctx.args[2]
        if not os.path.exists(os.path.expanduser(src)):
            raise VarnaError(f"no file {src}")
        tilde = (lambda p: "~" + os.path.abspath(os.path.expanduser(p))[len(core.HOME):]
                 if os.path.abspath(os.path.expanduser(p)).startswith(core.HOME) else os.path.abspath(p))
        entry = {"src": tilde(src), "dst": tilde(dst)}
        if ctx.opts.get("tool"):
            entry["tool"] = ctx.opts["tool"]
        conf["template"] = [t for t in conf["template"] if os.path.expanduser(t["dst"]) != os.path.expanduser(dst)] + [entry]
        core.render_user(conf, entry)   # check it renders before saving
        core.save_config(conf)
        ui.ok(f"{entry['src']} → {entry['dst']} on every apply")
        return report(core.apply(conf, only={entry.get("tool") or os.path.basename(dst)}))
    if what in ("remove", "rm"):
        dst = os.path.expanduser(ctx.args[1]) if len(ctx.args) > 1 else ""
        before = len(conf["template"])
        conf["template"] = [t for t in conf["template"] if os.path.expanduser(t["dst"]) != dst]
        if len(conf["template"]) == before:
            raise VarnaError(f"no template writes {ctx.args[1] if len(ctx.args) > 1 else '?'}")
        core.save_config(conf)
        ui.ok("removed (the file it wrote stays)")
        return 0
    if not conf["template"]:
        ui.out("No templates of yours.  varna template add <src> <dst>")
        return 0
    ui.table([[t["src"], t["dst"], t.get("tool", "desktop")] for t in conf["template"]], ["Template", "Writes", "Theme of"],
             title="Your templates")
    return 0


def cmd_palette(ctx):
    conf = core.load_config()
    values, t = core.resolve(conf, ctx.opts.get("tool"))
    ui.out(json.dumps(core.palette_json(values, t), indent=2))
    return 0


def cmd_ensure(ctx):
    written = core.ensure()
    if written:
        ui.note("wrote " + ", ".join(written))
    return 0


def cmd_doctor(ctx):
    problems = 0
    ui.header("Doctor")
    bad = [(tid, t) for tid, t in core.themes() if isinstance(t, VarnaError)]
    n = len(core.theme_paths())
    if bad:
        for tid, e in bad:
            ui.err(f"theme {tid}: {e}")
        problems += len(bad)
    else:
        ui.ok(f"{n} themes load")
    try:
        conf = core.load_config()
        core.resolve(conf)
        ui.ok(f"the desktop's theme: {conf['theme']}")
    except VarnaError as e:
        ui.err(str(e))
        return 1
    for name in core.TOOLS:
        if not core.tool_enabled(conf, name):
            continue
        try:
            core.render_tool(conf, name)
        except (VarnaError, OSError) as e:
            ui.err(f"{name}: {e}")
            problems += 1
            continue
        hook = core.hook_ok(name)
        if hook is False:
            path, _, line = core.HOOKS[name]
            ui.warn(f"{name}: {path} doesn't include varna's file yet: add  {c(line, 'peach')}")
            problems += 1
        elif not os.path.exists(core.out_path(name)):
            ui.warn(f"{name}: not written yet: varna apply")
            problems += 1
    ui.out()
    if problems:
        ui.warn("1 thing needs attention" if problems == 1 else f"{problems} things need attention")
    else:
        ui.ok(c("every tool takes the theme", "green", bold=True))
    return 1 if problems else 0


def report(results):
    failed = [r for r in results if r[1] == "failed"]
    for name, _, detail in failed:
        ui.err(f"{name}: {detail}")
    done = sum(1 for r in results if r[1] == "ok")
    ui.note(f"{done} tool{'s' if done != 1 else ''} themed" + (f", {len(failed)} failed" if failed else ""))
    return 1 if failed else 0


# ===================================================================== help
def help_all():
    ui.out(f"{c('❯', 'mauve', bold=True)} {c('varna', 'text', bold=True)} {c('वर्ण', 'mauve')}  {c('v' + VERSION, 'dim')}"
           f"   {c('one theme for every tool', 'dim')}\n")
    ui.out(f"{c('Usage', 'text', bold=True)}  varna [command] [options]      {c('varna alone shows the current theme', 'dim')}\n")
    groups = {}
    for name, d in COMMANDS.items():
        groups.setdefault(d["group"], []).append((name, d))
    for g, items in groups.items():
        ui.out(c(g.upper(), "mauve", bold=True))
        for name, d in items:
            al = f" ({', '.join(d['aliases'])})" if d["aliases"] else ""
            ui.out(f"  {c(name, 'text', bold=True):<24} {d['summary']}{c(al, 'dim')}")
        ui.out()
    ui.out(f"{c('OPTIONS', 'mauve', bold=True)}\n  --json        machine-readable (list)\n  --no-color    plain output (also NO_COLOR=1)\n"
           f"  -h, --help    help for varna or a command\n  -V            the version\n")
    ui.out(c("Docs: https://theyashsawarkar.github.io/varna/   ·   varna <command> --help for any command", "dim"))


def help_cmd(name):
    d = COMMANDS[name]
    ui.out(f"{c('varna ' + name, 'text', bold=True)} {d['args']}\n  {d['summary']}\n")
    if d.get("description"):
        import textwrap
        ui.out(textwrap.indent(textwrap.fill(d["description"], 88), "  ") + "\n")
    if d["aliases"]:
        ui.out(f"{c('ALIASES', 'mauve', bold=True)}  {', '.join(d['aliases'])}\n")
    ui.out(c("EXAMPLES", "mauve", bold=True))
    for e in d["examples"]:
        ui.out(f"  {c('$', 'dim')} {e}")


HANDLERS = {"status": cmd_status, "list": cmd_list, "apply": cmd_apply, "mode": cmd_mode, "show": cmd_show, "set": cmd_set, "tool": cmd_tool,
            "tools": cmd_tools, "new": cmd_new, "edit": cmd_edit, "delete": cmd_delete, "template": cmd_template,
            "palette": cmd_palette, "ensure": cmd_ensure, "doctor": cmd_doctor}


def main(argv):
    if "--no-color" in argv:
        ui.set_color(False)
        argv = [a for a in argv if a != "--no-color"]
    if not argv:
        argv = ["status"]
    cmd, rest = argv[0], argv[1:]
    if cmd in ("-h", "--help"):
        help_all()
        return 0
    if cmd in ("-V", "--version", "version"):
        ui.out(f"varna {VERSION}")
        return 0
    if cmd == "_themes":   # tab completion
        ui.out("\n".join(core.theme_paths()))
        return 0
    cmd = ALIASES.get(cmd, cmd)
    if cmd == "help":
        if rest and ALIASES.get(rest[0], rest[0]) in COMMANDS and rest[0] != "help":
            help_cmd(ALIASES.get(rest[0], rest[0]))
        else:
            help_all()
        return 0
    if cmd not in HANDLERS:
        if cmd in core.theme_paths():   # `varna nord` = `varna apply nord`
            cmd, rest = "apply", [cmd] + rest
        else:
            ui.err(f"no command {c(cmd, 'text', bold=True)}" + c("   varna help lists them", "dim"))
            return 2
    if {"-h", "--help"} & set(rest):
        help_cmd(cmd)
        return 0
    try:
        return HANDLERS[cmd](Ctx(rest)) or 0
    except VarnaError as e:
        ui.err(str(e))
        return 1
    except KeyboardInterrupt:
        ui.out()
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
