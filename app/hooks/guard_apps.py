#!/usr/bin/env python3
"""PreToolUse hook: computer use may only touch iPhone Mirroring.

The scheduler auto-approves Claude Code's per-session "allow app access"
prompt so runs can be unattended. This hook makes that safe: any
request_access / open_application call that names an app outside
config.json "allowed_apps" is blocked before the prompt can appear.
Exit code 2 = block the tool call and show stderr to the model.
"""
import json
import os
import sys
from pathlib import Path

COC_HOME = Path(os.environ.get("COC_HOME", Path.home() / ".coc-agent"))
ALIASES = {"com.apple.screencontinuity": "iphone mirroring"}


def norm(x) -> str:
    if isinstance(x, dict):
        x = x.get("displayName") or x.get("name") or x.get("bundleId") or x.get("app") or ""
    s = str(x).strip().lower()
    return ALIASES.get(s, s)


def main():
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)
    tool = event.get("tool_name", "")
    inp = event.get("tool_input") or {}
    try:  # merged config (defaults <- profile <- owner), so a slim config.json still works
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import cocconf
        cfg = cocconf.config()
    except Exception:
        try:
            cfg = json.loads((COC_HOME / "config.json").read_text())
        except Exception:
            cfg = {}
    allowed = {norm(a) for a in cfg.get("allowed_apps", ["iPhone Mirroring"])}

    if tool.endswith("__request_access"):
        apps = inp.get("apps") or []
        if isinstance(apps, (str, dict)):
            apps = [apps]
        requested = [norm(a) for a in apps]
    elif tool.endswith("__open_application"):
        requested = [norm(inp.get("app") or inp.get("name") or inp.get("bundleId") or "")]
    else:
        sys.exit(0)

    bad = [a for a in requested if a not in allowed]
    if bad or not requested:
        print(
            f"BLOCKED by coc-agent guard: only {sorted(allowed)} may be used; requested {requested}. "
            "Do not try other apps. If you are stuck, finish the run with status needs_human.",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
