#!/usr/bin/env python3
"""Owner-side configuration for coc-agent (called by `cocctl`; the agent never runs this).

  cocsetup.py setup [--profile NAME] [--yes]     guided setup (asks a few questions on a terminal)
  cocsetup.py profile list | show [NAME] | set NAME [--reset-tuning]
  cocsetup.py config show | get KEY | set KEY VALUE | unset KEY    (dotted keys, e.g. game_limits.use_gems)
  cocsetup.py migrate                            slim an old full-copy config.json so profiles apply
  cocsetup.py validate                           check config.json (profile exists, unknown keys)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cocconf  # noqa: E402

COC_HOME = cocconf.COC_HOME
CONFIG = COC_HOME / "config.json"
TUNING = COC_HOME / "memory" / "tuning.json"

BOLD, DIM, GRN, YEL, RED, OFF = "\033[1m", "\033[2m", "\033[32m", "\033[33m", "\033[31m", "\033[0m"
if not sys.stdout.isatty():
    BOLD = DIM = GRN = YEL = RED = OFF = ""


def read_user() -> dict:
    return cocconf.load_json(CONFIG, {}) or {}


def write_user(cfg: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG.with_suffix(f".json.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(cfg, indent=2) + "\n")
    os.replace(tmp, CONFIG)


def backup_user() -> Path | None:
    if not CONFIG.exists():
        return None
    bk = CONFIG.with_name(f"config.json.bak.{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy(CONFIG, bk)
    return bk


# ---------------------------------------------------------------- profiles
def profile_list(_args=None) -> None:
    active = cocconf.config().get("_profile")
    print(f"{BOLD}Strategy profiles{OFF}  (active: {active}; set with: cocctl profile set <name>)\n")
    for name in cocconf.list_profiles():
        p = cocconf.load_profile(name) or {}
        mark = f"{GRN}●{OFF}" if name == active else " "
        print(f"{mark} {BOLD}{name}{OFF}\n    {p.get('summary', '')}\n    {DIM}best for: {p.get('best_for', '')}{OFF}")


def profile_show(name: str | None) -> None:
    name = name or cocconf.config().get("_profile")
    p = cocconf.load_profile(name)
    if not p:
        sys.exit(f"unknown profile {name!r}; available: {', '.join(cocconf.list_profiles())}")
    print(p["direction"].rstrip())
    if p.get("config"):
        print(f"\n{DIM}config overlay (your config.json still wins):{OFF}")
        print(json.dumps(p["config"], indent=2))


def reset_tuning() -> int:
    t = cocconf.load_json(TUNING, None)
    if not t or not t.get("knobs"):
        return 0
    n = len(t["knobs"])
    shutil.copy(TUNING, TUNING.with_name(f"tuning.json.bak.{time.strftime('%Y%m%d-%H%M%S')}"))
    t["knobs"] = {}
    TUNING.write_text(json.dumps(t, indent=2) + "\n")
    return n


def profile_set(name: str, reset: bool = False) -> None:
    if not cocconf.load_profile(name):
        sys.exit(f"unknown profile {name!r}; available: {', '.join(cocconf.list_profiles())}")
    cfg = read_user()
    old = cocconf.active_profile_name(cocconf.deep_merge(cocconf.defaults(), cfg))
    cocconf.set_path(cfg, "strategy.profile", name)
    write_user(cfg)
    print(f"{GRN}✓{OFF} profile: {old} → {BOLD}{name}{OFF}")
    if reset:
        n = reset_tuning()
        print(f"{GRN}✓{OFF} cleared {n} tuned knob(s) (backup kept next to memory/tuning.json)")
    else:
        print(f"{DIM}Knobs the agent tuned under another profile are ignored while this one is active.{OFF}")
    if old != name:
        print("The next run re-derives the agent's strategy.md from the new profile.")


# ---------------------------------------------------------------- config
def config_show() -> None:
    cfg = cocconf.config()
    print(json.dumps({k: v for k, v in cfg.items() if not k.startswith("_") or k in ("_profile", "_profile_error")}, indent=2))


def config_get(key: str) -> None:
    try:
        print(json.dumps(cocconf.get_path(cocconf.config(), key), indent=2))
    except KeyError:
        sys.exit(f"no such key: {key}")


def config_set(key: str, value: str) -> None:
    cfg = read_user()
    val = cocconf.parse_value(value)
    if key == "strategy.profile" and not cocconf.load_profile(str(val)):
        sys.exit(f"unknown profile {val!r}; available: {', '.join(cocconf.list_profiles())}")
    if key == "strategy.notes" and isinstance(val, str):
        val = [val]
    cocconf.set_path(cfg, key, val)
    bad = cocconf.unknown_keys(cfg)
    if key in bad:
        print(f"{YEL}!{OFF} {key} isn't a known setting (typo?). Saved anyway.")
    write_user(cfg)
    print(f"{GRN}✓{OFF} {key} = {json.dumps(val)}")


def config_unset(key: str) -> None:
    cfg = read_user()
    parts = key.split(".")
    node = cfg
    for p in parts[:-1]:
        node = node.get(p) if isinstance(node, dict) else None
        if node is None:
            sys.exit(f"{key} is not set in config.json")
    if not isinstance(node, dict) or parts[-1] not in node:
        sys.exit(f"{key} is not set in config.json")
    del node[parts[-1]]
    write_user(cfg)
    print(f"{GRN}✓{OFF} {key} removed (the profile/default value applies again)")


def add_note(text: str) -> None:
    cfg = read_user()
    notes = ((cfg.get("strategy") or {}).get("notes")) or []
    if isinstance(notes, str):
        notes = [notes]
    notes.append(text)
    cocconf.set_path(cfg, "strategy.notes", notes)
    write_user(cfg)
    print(f"{GRN}✓{OFF} note added ({len(notes)} total). The agent reads it on every run via `coc direction`.")


def migrate() -> None:
    """Old installs copied the whole default file into config.json; that masks every profile value."""
    user = read_user()
    if not user:
        return
    slim = cocconf.slim_user_config(user)
    if slim != user:
        bk = backup_user()
        write_user(slim)
        print(f"{GRN}✓{OFF} config.json slimmed to your own settings only (so profiles apply); backup: {bk.name}")


def validate() -> int:
    problems = 0
    if CONFIG.exists() and cocconf.load_json(CONFIG) is None:
        print(f"{RED}✗{OFF} config.json is not valid JSON")
        return 1
    cfg = cocconf.config()
    if cfg.get("_profile_error"):
        print(f"{RED}✗{OFF} {cfg['_profile_error']}")
        problems += 1
    else:
        print(f"{GRN}✓{OFF} strategy profile: {cfg['_profile']}")
    for k in cocconf.unknown_keys():
        print(f"{YEL}!{OFF} unknown setting in config.json: {k} (typo?)")
        problems += 1
    style = (cfg.get("strategy") or {}).get("attack_style", "auto")
    attacks = (cocconf.APP / "knowledge" / "attacks.md").read_text() if (cocconf.APP / "knowledge" / "attacks.md").exists() else ""
    if style not in ("auto", "", None) and f"## {style}" not in attacks:
        print(f"{YEL}!{OFF} strategy.attack_style {style!r} isn't a recipe in app/knowledge/attacks.md (the agent will treat it as a hint)")
    for k in ("use_gems", "use_magic_items"):
        if (cfg.get("game_limits") or {}).get(k):
            print(f"{YEL}!{OFF} game_limits.{k} is ON: the agent may spend them")
    return problems


# ---------------------------------------------------------------- setup wizard
def ask(prompt: str, default: str = "") -> str:
    try:
        ans = input(f"{prompt} {DIM}[{default}]{OFF} ").strip()
    except EOFError:
        ans = ""
    return ans or default


def yes(prompt: str, default: bool) -> bool:
    return ask(prompt + " (y/n)", "y" if default else "n").lower().startswith("y")


def setup(profile: str | None, assume_yes: bool) -> None:
    cfg = read_user()
    merged = cocconf.config()
    interactive = sys.stdin.isatty() and not assume_yes
    names = cocconf.list_profiles()
    if profile:
        if profile not in names:
            sys.exit(f"unknown profile {profile!r}; available: {', '.join(names)}")
    elif interactive:
        profile_list()
        print()
        profile = ask("Which profile?", merged.get("_profile") or cocconf.DEFAULT_PROFILE)
        while profile not in names:
            profile = ask(f"Pick one of {', '.join(names)}:", cocconf.DEFAULT_PROFILE)
    else:
        profile = merged.get("_profile") or cocconf.DEFAULT_PROFILE
    cocconf.set_path(cfg, "strategy.profile", profile)

    if interactive:
        lim = merged.get("game_limits") or {}
        print(f"\n{BOLD}When are you asleep / away from the Mac?{OFF} The agent does most of its work then.")
        nh = merged.get("night_hours") or [["00:30", "08:30"]]
        start = ask("  night window start (HH:MM)", nh[0][0])
        end = ask("  night window end   (HH:MM)", nh[0][1])
        cocconf.set_path(cfg, "night_hours", [[start, end]])
        print(f"\n{BOLD}What may the agent do?{OFF}")
        for key, q in (("do_builder_base", "Play the Builder Base too?"),
                       ("allow_town_hall_upgrade", "Upgrade the Town Hall when the profile says it's time?"),
                       ("allow_new_buildings", "Build newly unlocked buildings from the Shop (gold/elixir only)?"),
                       ("use_magic_items", "Use magic items (books, hammers, potions, runes)?"),
                       ("donate_to_clan", "Donate spare troops to clan requests?"),
                       ("do_clan_capital", "Do Clan Capital raid attacks?"),
                       ("use_gems", "Spend gems (never real money)?")):
            cocconf.set_path(cfg, f"game_limits.{key}", yes(f"  {q}", bool(lim.get(key))))
        style = ask(f"\n{BOLD}Attack recipe{OFF} (auto, or a name from app/knowledge/attacks.md, e.g. edrag-zap)",
                    (merged.get("strategy") or {}).get("attack_style", "auto"))
        cocconf.set_path(cfg, "strategy.attack_style", style)
        model = ask(f"\n{BOLD}Claude model{OFF} for runs (blank = your default; a smaller model costs less)", merged.get("model") or "")
        if model:
            cfg["model"] = model
        note = ask(f"\n{BOLD}Anything else the agent should know?{OFF} (e.g. 'Archer Queen before King'; blank to skip)", "")
        if note:
            notes = ((cfg.get("strategy") or {}).get("notes")) or []
            cocconf.set_path(cfg, "strategy.notes", (notes if isinstance(notes, list) else [notes]) + [note])
    slim = cocconf.slim_user_config(cfg)
    slim.setdefault("strategy", {})["profile"] = profile  # keep the choice explicit even when it's the default
    write_user(slim)
    print(f"\n{GRN}✓{OFF} saved {CONFIG}")
    print(f"  profile {BOLD}{profile}{OFF}. Change any time: cocctl profile set <name>, cocctl config set <key> <value>, cocctl note \"...\"")


def main(argv: list[str]) -> None:
    if not argv:
        sys.exit(__doc__)
    cmd, rest = argv[0], argv[1:]
    if cmd == "setup":
        prof = rest[rest.index("--profile") + 1] if "--profile" in rest else None
        setup(prof, "--yes" in rest or "-y" in rest)
    elif cmd == "profile":
        sub = rest[0] if rest else "list"
        if sub == "list":
            profile_list()
        elif sub == "show":
            profile_show(rest[1] if len(rest) > 1 else None)
        elif sub == "set" and len(rest) > 1:
            profile_set(rest[1], "--reset-tuning" in rest)
        else:
            sys.exit("usage: cocctl profile list | show [name] | set <name> [--reset-tuning]")
    elif cmd == "config":
        sub = rest[0] if rest else "show"
        if sub == "show":
            config_show()
        elif sub == "get" and len(rest) == 2:
            config_get(rest[1])
        elif sub == "set" and len(rest) == 3:
            config_set(rest[1], rest[2])
        elif sub == "unset" and len(rest) == 2:
            config_unset(rest[1])
        else:
            sys.exit("usage: cocctl config show | get <key> | set <key> <value> | unset <key>")
    elif cmd == "note":
        if not rest:
            sys.exit('usage: cocctl note "Upgrade the Archer Queen before the King"')
        add_note(" ".join(rest))
    elif cmd == "migrate":
        migrate()
    elif cmd == "validate":
        sys.exit(1 if validate() else 0)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
