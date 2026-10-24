import itertools
import json
import os
import re
import sys
import tempfile
import unittest

ROOT = tempfile.mkdtemp()
os.environ.update(HOME=ROOT, XDG_CONFIG_HOME=os.path.join(ROOT, ".config"), XDG_STATE_HOME=os.path.join(ROOT, ".local", "state"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from varna import core  # noqa: E402


class Themes(unittest.TestCase):
    def test_every_shipped_theme_renders_every_tool(self):
        """No template may name a colour a theme lacks: every pair renders."""
        for tid in core.theme_paths():
            conf = {"theme": tid, "tools": {}, "ui": {}, "disabled": [], "template": [], "gtk": True}
            for tool in core.TOOLS:
                with self.subTest(theme=tid, tool=tool):
                    path, text = core.render_tool(conf, tool)
                    self.assertNotIn("{{", text)
                    self.assertTrue(text.strip())

    def test_light_themes_say_so(self):
        for tid in ("catppuccin-latte", "rose-pine-dawn"):
            values, t = core.resolve({"theme": tid})
            self.assertEqual(values["variant"], "light")
            self.assertGreater(core.luminance(values["base"]), core.luminance(values["text"]))

    def test_vayu_keeps_todays_colours(self):
        values, _ = core.resolve({"theme": "vayu"}, "tmux")
        self.assertEqual(values["accent"], "#cba6f7")
        self.assertEqual(values["accent2"], "#f5c2e7")
        self.assertEqual(values["urgent"], "#dc2626")
        self.assertEqual(values["window_idle"], "#9a9faa")   # a tmux extra


    def test_tmux_bar_capsules_stay_apart(self):
        """The bar's solid capsules can be on screen together (the session in
        any of its states, the current window, Claude waiting, usage full):
        in every theme they must be told apart at a glance."""
        far = 45   # RGB distance; below this two fills read as the same colour
        for tid in core.theme_paths():
            _, text = core.render_tool({"theme": tid, "tools": {}, "ui": {}, "disabled": [], "template": [], "gtk": True}, "tmux")
            v = dict(re.findall(r'set -g @(\w+) "(#[0-9a-f]{6})"', text))
            solid = {k: v[k] for k in ("accent", "prefix", "copy", "window", "attention", "error")}
            for (a, ca), (b, cb) in itertools.combinations(solid.items(), 2):
                d = sum((x - y) ** 2 for x, y in zip(core.hex_rgb(ca), core.hex_rgb(cb), strict=True)) ** .5
                with self.subTest(theme=tid, pair=f"{a}/{b}"):
                    self.assertGreaterEqual(d, far, f"{tid}: @{a} {ca} and @{b} {cb} look the same")


class Render(unittest.TestCase):
    ctx = {"accent": "#cba6f7", "base": "#1e1e2e", "gaps": 4}

    def test_filters(self):
        r = lambda s: core.render(s, self.ctx)
        self.assertEqual(r("{{accent}}"), "#cba6f7")
        self.assertEqual(r("{{accent:upper}}"), "#CBA6F7")
        self.assertEqual(r("{{accent:bare}}"), "cba6f7")
        self.assertEqual(r("{{base:a=0.35}}"), "#1e1e2e59")
        self.assertEqual(r("{{accent:rgb}}"), "203, 166, 247")
        self.assertEqual(r("{{accent:rgba=0.4}}"), "rgba(203, 166, 247, 0.4)")
        self.assertEqual(r("{{accent:alpha=0.4}}"), "alpha(#cba6f7, 0.4)")
        self.assertEqual(r("{{gaps}}"), "4")

    def test_fallbacks_and_typos(self):
        self.assertEqual(core.render("{{nope|accent}}", self.ctx), "#cba6f7")
        self.assertEqual(core.render("{{nope|#123456}}", self.ctx), "#123456")
        with self.assertRaises(core.VarnaError):
            core.render("{{acent}}", self.ctx)
        with self.assertRaises(core.VarnaError):
            core.render("{{gaps:a=0.5}}", self.ctx)

    def test_conditions(self):
        text = "a\n?swayfx corner_radius 12\n?!swayfx plain\nb\n"
        self.assertEqual(core.conditions(text, {"swayfx": True}), "a\ncorner_radius 12\nb\n")
        self.assertEqual(core.conditions(text, {"swayfx": False}), "a\nplain\nb\n")


class Resolve(unittest.TestCase):
    def test_accent_override_and_tool_picks(self):
        conf = {"theme": "vayu", "accent": "blue", "tools": {"nvim": "nord", "kitty": {"opacity": 0.95}}, "ui": {}}
        desk, _ = core.resolve(conf)
        self.assertEqual(desk["accent"], desk["blue"])
        nvim, t = core.resolve(conf, "nvim")
        self.assertEqual(t["id"], "nord")
        self.assertNotEqual(nvim["accent"], desk["blue"])   # a tool with its own theme keeps that theme's accent
        kitty, t = core.resolve(conf, "kitty")
        self.assertEqual((t["id"], kitty["opacity"]), ("vayu", 0.95))

    def test_roles_chain_and_bad_roles(self):
        values, _ = core.resolve({"theme": "catppuccin-mocha"})
        self.assertEqual(values["border"], values["accent"])   # border -> accent -> mauve
        with self.assertRaises(core.VarnaError):
            core.resolve({"theme": "vayu", "accent": "notacolour"})


class Config(unittest.TestCase):
    def test_round_trip(self):
        conf = {"theme": "nord", "accent": "#ff0000", "gtk": True, "tools": {"nvim": "kanagawa", "kitty": {"opacity": 0.9}},
                "ui": {"gaps": 8, "font": "Inter"}, "disabled": ["lazygit"],
                "template": [{"src": "~/a.varna", "dst": "~/a", "tool": "waybar"}]}
        core.save_config(conf)
        back = core.load_config()
        for k in ("theme", "accent", "gtk", "tools", "ui", "disabled", "template"):
            self.assertEqual(back[k], conf[k], k)

    def test_set_value_validates(self):
        core.save_config({"theme": "vayu", "tools": {}, "ui": {}})
        core.set_value("ui.gaps", "8")
        self.assertEqual(core.load_config()["ui"]["gaps"], 8)
        with self.assertRaises(core.VarnaError):
            core.set_value("theme", "no-such-theme")
        with self.assertRaises(core.VarnaError):
            core.set_value("ui.nope", "1")


class Apply(unittest.TestCase):
    def test_writes_every_tool_and_a_tools_own_theme(self):
        conf = {"theme": "vayu", "tools": {"tmux": "gruvbox"}, "ui": {}, "disabled": [], "template": []}
        results = core.apply(conf, reload=False)
        self.assertFalse([r for r in results if r[1] == "failed"], results)
        tmux = open(os.path.join(core.STATE, "tmux.conf")).read()
        gruv, _ = core.resolve(conf, "tmux")
        self.assertIn(gruv["accent"], tmux)
        pal = json.load(open(os.path.join(core.STATE, "palette.json")))
        self.assertEqual(pal["theme"], "vayu")

    def test_user_template(self):
        src = os.path.join(ROOT, "x.varna")
        open(src, "w").write("color={{accent:upper}}\n")
        conf = {"theme": "vayu", "tools": {}, "ui": {}, "disabled": [], "template": [{"src": src, "dst": os.path.join(ROOT, "x")}]}
        core.apply(conf, reload=False)
        self.assertEqual(open(os.path.join(ROOT, "x")).read(), "color=#CBA6F7\n")

    def test_throwaway_home_never_reloads(self):
        called = []
        old = dict(core.RELOADERS)
        try:
            for k in core.RELOADERS:
                core.RELOADERS[k] = lambda conf, k=k: called.append(k)
            core.apply({"theme": "vayu", "tools": {}, "ui": {}, "disabled": [], "template": []}, reload=True)
        finally:
            core.RELOADERS.update(old)
        self.assertFalse(core.live_home())
        self.assertEqual(called, [])

    def test_own_themes(self):
        tid, path = core.copy_theme("nord", "My Nord")
        self.assertEqual(tid, "my-nord")
        self.assertTrue(core.load_theme(tid)["user"])
        core.delete_theme(tid)
        with self.assertRaises(core.VarnaError):
            core.delete_theme("nord")


if __name__ == "__main__":
    unittest.main()
