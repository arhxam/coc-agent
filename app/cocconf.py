"""Shared config loading for coc-agent (scheduler, the `coc` helper, hooks, cocctl).

Layers, lowest to highest priority:

    app/config.default.json            shipped defaults
    app/profiles/<profile>.json        the strategy profile's "config" overlay
    ~/.coc-agent/config.json           the owner's own settings (always wins)

The game knobs the agent can tune are layered once more on top of that by
`coc` (memory/tuning.json, clamped to game_limits).

The active profile is `strategy.profile` from the merged default+user config
(the profile can't choose itself).
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

COC_HOME = Path(os.environ.get("COC_HOME", Path.home() / ".coc-agent"))
APP = Path(__file__).resolve().parent
PROFILES = APP / "profiles"
DEFAULT_PROFILE = "max-out"

# Keys the agent may tune (memory/tuning.json) and the hard limit that caps each one.
LIMIT_FOR = {
    "attacks_per_run": "max_attacks_per_run",
    "next_per_attack": "max_next_per_attack",
    "walls_per_run": "max_walls_per_run",
}


def load_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError, NotADirectoryError):
        return default


def deep_merge(base: dict, over: dict) -> dict:
    """Recursive merge; dicts merge, everything else (lists included) is replaced."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def defaults() -> dict:
    return load_json(APP / "config.default.json", {}) or {}


def user_config() -> dict:
    return load_json(COC_HOME / "config.json", {}) or {}


def list_profiles() -> list[str]:
    return sorted(p.stem for p in PROFILES.glob("*.json"))


def load_profile(name: str) -> dict | None:
    """{'name','summary','best_for','config':{...},'direction': markdown} or None if unknown."""
    if not name or "/" in name or name.startswith("."):
        return None
    meta = load_json(PROFILES / f"{name}.json")
    if meta is None:
        return None
    md = PROFILES / f"{name}.md"
    meta = dict(meta)
    meta.setdefault("name", name)
    meta["direction"] = md.read_text() if md.exists() else ""
    return meta


def active_profile_name(cfg_wo_profile: dict | None = None) -> str:
    base = cfg_wo_profile if cfg_wo_profile is not None else deep_merge(defaults(), user_config())
    return str(((base.get("strategy") or {}).get("profile")) or DEFAULT_PROFILE)


def config() -> dict:
    """The fully merged config. `_profile` holds the active profile name, and
    `_profile_error` is set when the configured profile doesn't exist."""
    d, u = defaults(), user_config()
    name = active_profile_name(deep_merge(d, u))
    prof = load_profile(name)
    cfg = deep_merge(d, (prof or {}).get("config") or {})
    cfg = deep_merge(cfg, u)
    cfg["_profile"] = name
    if prof is None:
        cfg["_profile_error"] = f"unknown profile {name!r}; available: {', '.join(list_profiles())}"
    return cfg


def _leaf_paths(d: dict, prefix=()):
    for k, v in d.items():
        if isinstance(v, dict) and v:
            yield from _leaf_paths(v, prefix + (k,))
        else:
            yield prefix + (k,), v


def unknown_keys(user: dict | None = None) -> list[str]:
    """Dotted keys in the owner's config.json that the defaults don't know (typo check).
    Keys under game/strategy are open-ended and not checked below their first level."""
    d = defaults()
    user = user_config() if user is None else user
    out = []
    for path, _ in _leaf_paths(user):
        if path[0].startswith("_") or (len(path) > 1 and path[-1].startswith("_")):
            continue
        node = d
        for i, part in enumerate(path):
            if isinstance(node, dict) and part in node:
                node = node[part]
                if path[0] in ("game", "strategy") and i >= 1:
                    break
            else:
                if path[0] == "game" and i >= 1:
                    break  # extra starting knobs are fine
                out.append(".".join(path))
                break
    return out


def slim_user_config(user: dict) -> dict:
    """Drop leaves that equal the shipped default, so profiles can apply to them.
    (Older installs copied the whole default file into config.json, which masked
    every profile value.)"""
    d = defaults()

    def slim(u, base):
        res = {}
        for k, v in u.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                sub = slim(v, base[k])
                if sub:
                    res[k] = sub
            elif k not in base or base[k] != v:
                res[k] = v
        return res

    return slim(user, d)


def get_path(cfg: dict, dotted: str):
    node = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(dotted)
        node = node[part]
    return node


def set_path(cfg: dict, dotted: str, value) -> dict:
    parts = dotted.split(".")
    node = cfg
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = value
    return cfg


def parse_value(text: str):
    """CLI value → JSON value when it parses (true, 3, [..]), else the plain string."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text
