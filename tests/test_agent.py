"""Tests for the parts of coc-agent that don't need a Mac, an iPhone or Claude:
config layering and profiles, the `coc` helper, the scheduler's pure logic, and the guard hook.

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APP = REPO / "app"
COC = APP / "tools" / "coc.py"
SETUP = APP / "tools" / "cocsetup.py"
sys.path.insert(0, str(APP))
import cocconf  # noqa: E402


class Home:
    """A throwaway COC_HOME with seeded memory."""

    def __init__(self, user_config: dict | None = None):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name)
        for d in ("memory", "logs", "state"):
            (self.path / d).mkdir()
        for f in (APP / "memory_seed").iterdir():
            (self.path / "memory" / f.name).write_text(f.read_text())
        if user_config is not None:
            (self.path / "config.json").write_text(json.dumps(user_config))
        self.env = {**os.environ, "COC_HOME": str(self.path), "COC_RESULT_FILE": str(self.path / "state/run_result.json")}

    def run(self, script: Path, *args, check=True) -> subprocess.CompletedProcess:
        p = subprocess.run([sys.executable, str(script), *args], env=self.env, capture_output=True, text=True)
        if check and p.returncode != 0:
            raise AssertionError(f"{script.name} {args} failed ({p.returncode}):\n{p.stdout}\n{p.stderr}")
        return p

    def coc(self, *args, check=True):
        return self.run(COC, *args, check=check)

    def config(self) -> dict:
        return json.loads(self.coc("config").stdout)

    def py(self, code: str) -> str:
        p = subprocess.run([sys.executable, "-c", code], env=self.env, capture_output=True, text=True, cwd=str(APP))
        if p.returncode != 0:
            raise AssertionError(p.stderr)
        return p.stdout

    def close(self):
        self.dir.cleanup()


class ProfilesTest(unittest.TestCase):
    def test_every_profile_is_complete_and_uses_known_keys(self):
        names = cocconf.list_profiles()
        self.assertIn(cocconf.DEFAULT_PROFILE, names)
        self.assertGreaterEqual(len(names), 5)
        for name in names:
            p = cocconf.load_profile(name)
            self.assertTrue(p["summary"] and p["best_for"], name)
            self.assertIsInstance(p["config"], dict, name)
            self.assertGreater(len(p["direction"]), 200, f"{name}.md missing or too short")
            self.assertEqual(cocconf.unknown_keys(p["config"]), [], f"{name} overlay has unknown keys")

    def test_default_config_and_shipped_profile(self):
        d = cocconf.defaults()
        self.assertEqual(d["strategy"]["profile"], cocconf.DEFAULT_PROFILE)
        self.assertFalse(d["game_limits"]["use_gems"])
        self.assertFalse(d["game_limits"]["use_magic_items"])

    def test_attack_styles_named_in_profiles_exist(self):
        attacks = (APP / "knowledge" / "attacks.md").read_text()
        for name in ("edrag-zap", "mass-dragon", "sneaky-goblin", "barch"):
            self.assertIn(f"## {name}", attacks)

    def test_unknown_profile_names_are_rejected_safely(self):
        self.assertIsNone(cocconf.load_profile("../config.default"))
        self.assertIsNone(cocconf.load_profile("nope"))


class ConfigLayeringTest(unittest.TestCase):
    def test_deep_merge(self):
        a = {"x": {"y": 1, "z": 2}, "l": [1, 2]}
        b = {"x": {"y": 5}, "l": [3]}
        self.assertEqual(cocconf.deep_merge(a, b), {"x": {"y": 5, "z": 2}, "l": [3]})
        self.assertEqual(a["x"]["y"], 1, "inputs must not be mutated")

    def test_profile_overlays_defaults_and_user_wins(self):
        h = Home({"strategy": {"profile": "war-ready"}, "game": {"walls_per_run": 7}})
        try:
            c = h.config()
            self.assertEqual(c["profile"], "war-ready")
            self.assertEqual(c["knobs"]["walls_per_day_target"], 12)  # from the profile
            self.assertEqual(c["knobs"]["walls_per_run"], 7)  # the owner's value wins
            self.assertEqual(c["knobs"]["storage_target_fill"], 0.9)  # default
        finally:
            h.close()

    def test_profile_can_set_scheduler_keys(self):
        h = Home({"strategy": {"profile": "frugal"}})
        try:
            out = h.py("import scheduler, json; c = scheduler.config(); print(json.dumps([c['max_runs_per_day'], c['opportunistic']['enabled'], c['opportunistic']['min_idle_minutes']]))")
            self.assertEqual(json.loads(out), [6, False, 20])
        finally:
            h.close()

    def test_unknown_profile_falls_back_with_error(self):
        h = Home({"strategy": {"profile": "nope"}})
        try:
            c = h.config()
            self.assertIn("profile_error", c)
            self.assertIn("WARNING", h.coc("direction").stdout)
        finally:
            h.close()

    def test_slim_user_config_drops_copied_defaults(self):
        full = cocconf.defaults()
        full["night_hours"] = [["01:00", "07:00"]]
        full["presence"]["home_gateway_macs"] = ["aa:bb:cc:dd:ee:ff"]
        slim = cocconf.slim_user_config(full)
        self.assertEqual(slim, {"night_hours": [["01:00", "07:00"]], "presence": {"home_gateway_macs": ["aa:bb:cc:dd:ee:ff"]}})

    def test_unknown_keys(self):
        self.assertEqual(cocconf.unknown_keys({"game": {"new_knob": 1}, "strategy": {"notes": ["x"]}}), [])
        self.assertEqual(cocconf.unknown_keys({"nigth_hours": [], "game_limits": {"use_gem": True}}),
                         ["nigth_hours", "game_limits.use_gem"])


class CocHelperTest(unittest.TestCase):
    def setUp(self):
        self.h = Home({})

    def tearDown(self):
        self.h.close()

    def test_tune_is_clamped_and_scoped_to_profile(self):
        self.h.coc("tune", "attacks_per_run", "99", "--why", "test")
        self.assertEqual(self.h.config()["knobs"]["attacks_per_run"], 5)  # max_attacks_per_run
        self.h.run(SETUP, "profile", "set", "endgame")
        c = self.h.config()
        self.assertEqual(c["knobs"]["attacks_per_run"], 3)  # endgame's value; max-out tuning ignored
        self.assertIn("attacks_per_run", c["tuning_ignored_other_profile"])

    def test_hard_limits_cannot_be_tuned(self):
        p = self.h.coc("tune", "use_gems", "true", "--why", "x", check=False)
        self.assertNotEqual(p.returncode, 0)

    def test_at_and_finish(self):
        self.assertRegex(self.h.coc("at", "1d 2h 3m").stdout.strip(), r"^\d{4}-\d\d-\d\dT")
        self.assertNotEqual(self.h.coc("at", "soon", check=False).returncode, 0)
        p = self.h.coc("finish", "--status", "ok", "--next", "+1h", "--reason", "r", "--summary", "s")
        self.assertIn("RUN RESULT WRITTEN", p.stdout)
        res = json.loads((self.h.path / "state/run_result.json").read_text())
        self.assertEqual(res["status"], "ok")
        self.assertNotEqual(self.h.coc("finish", "--status", "bogus", "--next", "+1h", "--reason", "r", "--summary", "s",
                                       check=False).returncode, 0)

    def test_experiment_one_at_a_time_and_measured(self):
        for g in (1_000_000, 1_200_000):
            self.h.coc("log", "attack", json.dumps({"strategy": "base-v1", "loot": {"gold": g, "elixir": 0}}))
        self.h.coc("experiment", "start", "pickier", "--hypothesis", "more loot")
        self.assertNotEqual(self.h.coc("experiment", "start", "other", "--hypothesis", "x", check=False).returncode, 0)
        self.h.coc("log", "attack", json.dumps({"strategy": "base-v1", "loot": {"gold": 2_200_000, "elixir": 0}}))
        st = json.loads(self.h.coc("experiment", "status").stdout)
        self.assertEqual(st["attacks_after"], 1)
        self.assertEqual(st["avg_before"], 1_100_000)
        self.assertEqual(st["change_pct"], 100.0)
        self.h.coc("experiment", "end", "--result", "keep")
        self.assertIn("no open experiment", self.h.coc("experiment", "status").stdout)

    def test_daily_attack_cap_warning_and_today(self):
        h = Home({"game_limits": {"max_attacks_per_day": 2}})
        try:
            h.coc("log", "attack", json.dumps({"strategy": "x"}))
            self.assertNotIn("CAP REACHED", h.coc("log", "attack", json.dumps({"strategy": "bb-drag"})).stdout)
            self.assertIn("CAP REACHED", h.coc("log", "attack", json.dumps({"strategy": "x"})).stdout)
            t = json.loads(h.coc("today").stdout)
            self.assertEqual((t["attacks_home"], t["attacks_builder_base"], t["attacks_left_today"]), (2, 1, 0))
        finally:
            h.close()

    def test_progress_and_stats_run(self):
        self.h.coc("log", "snapshot", json.dumps({"gold": 5, "elixir": 5, "caps": {"gold": 10, "elixir": 10},
                                                  "builders_idle": 1, "builders_total": 4, "lab_idle": False, "town_hall": 12}))
        out = self.h.coc("progress", "--days", "1").stdout
        self.assertIn(" 75%", out)  # 3 of 4 builders busy
        self.assertIn("100%", out)  # lab busy
        self.h.coc("stats", "--days", "1")
        self.h.coc("suggest-wake")
        self.h.coc("timers")
        self.h.coc("availability")

    def test_direction_includes_notes_and_switches(self):
        self.h.run(SETUP, "note", "Archer Queen before King")
        out = self.h.coc("direction").stdout
        self.assertIn("Profile: max-out", out)
        self.assertIn("Archer Queen before King", out)
        self.assertIn("use_gems=off", out)


class SetupTest(unittest.TestCase):
    def test_config_set_get_unset(self):
        h = Home({})
        try:
            h.run(SETUP, "config", "set", "game_limits.do_builder_base", "true")
            self.assertEqual(h.run(SETUP, "config", "get", "game_limits.do_builder_base").stdout.strip(), "true")
            self.assertNotEqual(h.run(SETUP, "config", "set", "strategy.profile", "nope", check=False).returncode, 0)
            h.run(SETUP, "config", "unset", "game_limits.do_builder_base")
            self.assertEqual(h.run(SETUP, "config", "get", "game_limits.do_builder_base").stdout.strip(), "false")
        finally:
            h.close()

    def test_noninteractive_setup_and_migrate(self):
        full = cocconf.defaults()
        full.pop("strategy")
        full["night_hours"] = [["23:00", "07:00"]]
        h = Home(full)
        try:
            h.run(SETUP, "migrate")
            self.assertEqual(json.loads((h.path / "config.json").read_text()), {"night_hours": [["23:00", "07:00"]]})
            h.run(SETUP, "setup", "--profile", "trophy-push", "--yes")
            self.assertEqual(h.config()["knobs"]["attack_goal"], "trophies")
            self.assertEqual(h.run(SETUP, "validate", check=False).returncode, 0)
        finally:
            h.close()


class SchedulerTest(unittest.TestCase):
    def test_windows_prompt_and_weekly(self):
        h = Home({})
        try:
            out = h.py(
                "import scheduler as s, datetime as dt, json\n"
                "t = dt.datetime(2026, 11, 29, 2, 0).astimezone()\n"  # a Sunday, 02:00
                "w = [['00:30', '08:30']]\n"
                "x = [['22:00', '06:00']]\n"
                "p = s.build_prompt('r', 'scheduled', {'reason': 'x', 'last_profile': 'endgame'}, True, None, weekly=True)\n"
                "print(json.dumps({'in': s.in_window(w, t) is not None, 'cross': s.in_window(x, t) is not None,\n"
                "  'out': s.in_window(w, t.replace(hour=9)) is None, 'weekly': s.weekly_review_due({}, {}, t),\n"
                "  'weekly_recent': s.weekly_review_due({}, {'last_weekly_review_at': t.isoformat()}, t),\n"
                "  'first': s.first_run(), 'prompt': p}))")
            r = json.loads(out)
            self.assertTrue(r["in"] and r["cross"] and r["out"] and r["weekly"] and r["first"])
            self.assertFalse(r["weekly_recent"])
            for needle in ("Strategy profile: max-out", "ONBOARDING SURVEY", "CHANGED the strategy profile", "WEEKLY REVIEW"):
                self.assertIn(needle, r["prompt"])
        finally:
            h.close()


class GuardHookTest(unittest.TestCase):
    def hook(self, payload: dict) -> int:
        h = Home({})
        try:
            return subprocess.run([sys.executable, str(APP / "hooks" / "guard_apps.py")], input=json.dumps(payload),
                                  env=h.env, capture_output=True, text=True).returncode
        finally:
            h.close()

    def test_only_iphone_mirroring(self):
        self.assertEqual(self.hook({"tool_name": "mcp__computer-use__request_access", "tool_input": {"apps": ["iPhone Mirroring"]}}), 0)
        self.assertEqual(self.hook({"tool_name": "mcp__computer-use__request_access", "tool_input": {"apps": ["Safari"]}}), 2)
        self.assertEqual(self.hook({"tool_name": "mcp__computer-use__open_application", "tool_input": {"app": "Terminal"}}), 2)
        self.assertEqual(self.hook({"tool_name": "mcp__computer-use__screenshot", "tool_input": {}}), 0)


class ShellTest(unittest.TestCase):
    def test_cocctl_syntax(self):
        self.assertEqual(subprocess.run(["bash", "-n", str(REPO / "bin" / "cocctl")]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
