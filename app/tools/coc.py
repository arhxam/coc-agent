#!/usr/bin/env python3
"""`coc` - the helper the in-game agent calls through Bash.

It does everything an LLM should not do in its head: clock math, appending logs,
computing stats from history, learning when the owner is away, and writing the
run result the scheduler reads.

  time
    coc now                          current local time + whether it's the night window
    coc at "1d 4h 30m"               ISO timestamp of now + an in-game timer
  memory / timing
    coc timers                       builder / lab / army timers recorded in memory/base.json
    coc suggest-wake [--need-loot]   next-wake candidates (timers + night window + availability)
    coc availability [--days 14]     when the system can actually run, learned from presence samples
  learning
    coc stats [--days 3]             runs, attacks, loot/attack, walls/day, storage fill, idle builders
    coc config                       current game knobs (defaults + your tuning, clamped to limits)
    coc tune <key> <value> --why ".."   change a knob in memory/tuning.json (logged)
    coc log <kind> '<json>'          kinds: attack upgrade research wall snapshot experiment event
  end of run
    coc finish --status ok --next "+2h10m" --reason "..." --summary "..."
               [--opportunistic-after "+40m" --opportunistic-why "army ready, storages 70%"]
"""
import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

COC_HOME = Path(os.environ.get("COC_HOME", Path.home() / ".coc-agent"))
STATE = COC_HOME / "state"
LOGS = COC_HOME / "logs"
MEMORY = COC_HOME / "memory"
RESULT_FILE = Path(os.environ.get("COC_RESULT_FILE", STATE / "run_result.json"))
RUN_ID = os.environ.get("COC_RUN_ID", "manual")

VALID_STATUS = {
    "ok",               # normal run finished
    "phone_in_use",     # iPhone Mirroring unavailable / iPhone unlocked / CoC open elsewhere
    "game_unavailable", # maintenance, update required, personal break, server error
    "needs_human",      # something only the owner can fix (permissions, login, update, captcha)
    "error",            # anything else went wrong
}
LOG_KINDS = {"attack", "upgrade", "research", "wall", "snapshot", "experiment", "event"}
LIMIT_FOR = {"attacks_per_run": "max_attacks_per_run", "next_per_attack": "max_next_per_attack",
             "walls_per_run": "max_walls_per_run"}


# ---------------------------------------------------------------- basics
def now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def iso(t: dt.datetime) -> str:
    return t.astimezone().isoformat(timespec="seconds")


DUR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(d|h|m|s)", re.I)


def parse_duration(text: str) -> dt.timedelta:
    """'1d 4h 30m', '4h', '+45m', '2h 5m 10s' -> timedelta."""
    text = text.strip().lstrip("+")
    parts = DUR_RE.findall(text)
    if not parts or DUR_RE.sub("", text).strip():
        raise ValueError(f"cannot parse duration {text!r}; use e.g. '1d 4h 30m'")
    mult = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    return dt.timedelta(seconds=sum(float(n) * mult[u.lower()] for n, u in parts))


def parse_when(text: str) -> dt.datetime:
    """Accepts '+1h 20m' / '1h 20m' (relative) or an ISO timestamp."""
    text = text.strip()
    try:
        t = dt.datetime.fromisoformat(text)
        return t if t.tzinfo else t.astimezone()
    except ValueError:
        return now() + parse_duration(text)


def parse_ts(value):
    if not value:
        return None
    try:
        t = dt.datetime.fromisoformat(str(value))
        return t if t.tzinfo else t.astimezone()
    except ValueError:
        return None


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)


def read_jsonl(path: Path, since: dt.datetime | None = None, key: str = "ts"):
    out = []
    try:
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = parse_ts(r.get(key) or r.get("started_at") or r.get("deferred_at"))
            if since and (not t or t < since):
                continue
            r["_t"] = t
            out.append(r)
    except FileNotFoundError:
        pass
    return out


def fmt_left(delta: dt.timedelta) -> str:
    s = int(delta.total_seconds())
    if s <= 0:
        return "done"
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m = s // 60
    return " ".join(p for p in (f"{d}d" if d else "", f"{h}h" if h else "", f"{m}m") if p)


def full_config() -> dict:
    cfg = load_json(COC_HOME / "app" / "config.default.json", {}) or {}
    user = load_json(COC_HOME / "config.json", {}) or {}
    for k, v in user.items():
        cfg[k] = {**cfg[k], **v} if isinstance(v, dict) and isinstance(cfg.get(k), dict) else v
    return cfg


def game_knobs() -> tuple[dict, dict]:
    """(knobs, limits): config 'game' defaults overlaid with memory/tuning.json, clamped to game_limits."""
    cfg = full_config()
    limits = {k: v for k, v in (cfg.get("game_limits") or {}).items() if not k.startswith("_")}
    knobs = {k: v for k, v in (cfg.get("game") or {}).items() if not k.startswith("_")}
    tuning = load_json(MEMORY / "tuning.json", {}) or {}
    for k, v in (tuning.get("knobs") or {}).items():
        knobs[k] = v.get("value") if isinstance(v, dict) else v
    for k, lim in LIMIT_FOR.items():
        if k in knobs and lim in limits and isinstance(knobs[k], (int, float)):
            knobs[k] = min(knobs[k], limits[lim])
    return knobs, limits


def window_end(windows, t: dt.datetime):
    for start_s, end_s in windows or []:
        sh, sm = map(int, start_s.split(":"))
        eh, em = map(int, end_s.split(":"))
        start = t.replace(hour=sh, minute=sm, second=0, microsecond=0)
        end = t.replace(hour=eh, minute=em, second=0, microsecond=0)
        if start <= end:
            if start <= t < end:
                return end
        elif t >= start:
            return end + dt.timedelta(days=1)
        elif t < end:
            return end
    return None


def next_window_start(windows, t: dt.datetime):
    best = None
    for start_s, _ in windows or []:
        sh, sm = map(int, start_s.split(":"))
        s = t.replace(hour=sh, minute=sm, second=0, microsecond=0)
        if s <= t:
            s += dt.timedelta(days=1)
        best = s if best is None or s < best else best
    return best


# ---------------------------------------------------------------- commands
def cmd_now(_):
    t = now()
    cfg = full_config()
    end = window_end(cfg.get("night_hours"), t)
    print(json.dumps({"now": iso(t), "epoch": int(t.timestamp()), "weekday": t.strftime("%A"),
                      "night_window": bool(end), "night_ends": iso(end) if end else None,
                      "next_night_starts": iso(next_window_start(cfg.get("night_hours"), t)) if not end else None}))


def cmd_at(a):
    print(iso(now() + parse_duration(a.duration)))


def collect_timers(base: dict):
    for b in (base.get("builders") or {}).get("busy") or []:
        yield f"builder: {b.get('target', '?')}", parse_ts(b.get("finishes_at"))
    lab = (base.get("lab") or {}).get("busy")
    if lab:
        yield f"lab: {lab.get('target', '?')}", parse_ts(lab.get("finishes_at"))
    pet = (base.get("pet_house") or {}).get("busy") if isinstance(base.get("pet_house"), dict) else None
    if pet:
        yield f"pet house: {pet.get('target', '?')}", parse_ts(pet.get("finishes_at"))
    for name, h in (base.get("heroes") or {}).items():
        if isinstance(h, dict) and h.get("upgrading_until"):
            yield f"hero: {name}", parse_ts(h.get("upgrading_until"))
    army = base.get("army") or {}
    if army.get("ready_at"):
        yield "army ready", parse_ts(army.get("ready_at"))


def cmd_timers(_):
    base = load_json(MEMORY / "base.json", {}) or {}
    t = now()
    rows = sorted(((lbl, ts) for lbl, ts in collect_timers(base) if ts), key=lambda r: r[1])
    b = base.get("builders") or {}
    print(f"now: {iso(t)}")
    print(f"builders: {len(b.get('busy') or [])}/{b.get('total', '?')} busy (memory updated {base.get('updated_at')})")
    for lbl, ts in rows:
        print(f"  {fmt_left(ts - t):>12}  {iso(ts)}  {lbl}")
    if not rows:
        print("  (no timers recorded)")


def availability_profile(days: int = 14):
    """Per hour-of-day: share of presence samples where a run could have happened
    (at home, screen unlocked, Mac idle >= 5 min, iPhone not known-away)."""
    since = now() - dt.timedelta(days=days)
    samples = read_jsonl(LOGS / "presence.jsonl", since)
    by_hour = collections.defaultdict(lambda: [0, 0])
    for s in samples:
        h = s["_t"].hour
        ok = (s.get("at_home") is not False and not s.get("screen_locked")
              and (s.get("mac_idle_s") or 0) >= 300 and s.get("iphone_nearby") is not False)
        by_hour[h][0] += int(ok)
        by_hour[h][1] += 1
    runs = read_jsonl(LOGS / "runs.jsonl", since, key="started_at")
    run_by_hour = collections.defaultdict(lambda: collections.Counter())
    for r in runs:
        if r.get("_t"):
            run_by_hour[r["_t"].hour][r.get("status", "?")] += 1
    return by_hour, run_by_hour, len(samples)


def cmd_availability(a):
    by_hour, run_by_hour, n = availability_profile(a.days)
    print(f"availability over the last {a.days} days ({n} presence samples, every ~5 min)")
    print("hour  runnable  runs (ok / phone_in_use / deferred / other)")
    for h in range(24):
        ok, tot = by_hour.get(h, [0, 0])
        rc = run_by_hour.get(h, collections.Counter())
        bar = "█" * round(10 * ok / tot) if tot else ""
        pct = f"{100 * ok / tot:3.0f}%" if tot else "  - "
        other = sum(rc.values()) - rc["ok"] - rc["phone_in_use"] - rc["deferred"]
        print(f"{h:02d}:00 {pct} {bar:<10}  {rc['ok']}/{rc['phone_in_use']}/{rc['deferred']}/{other}")
    if n < 50:
        print("(little data yet - assume night window is best, daytime only when owner is idle)")


def cmd_suggest_wake(a):
    base = load_json(MEMORY / "base.json", {}) or {}
    cfg = full_config()
    t = now()
    min_gap = dt.timedelta(minutes=cfg.get("min_interval_minutes", 15))
    max_gap = dt.timedelta(minutes=cfg.get("max_interval_minutes", 360))
    buffer = dt.timedelta(minutes=2)
    cands = []
    b = base.get("builders") or {}
    if b.get("total") is not None and len(b.get("busy") or []) < b["total"]:
        cands.append((t + min_gap, "a builder is idle right now"))
    for lbl, ts in collect_timers(base):
        if not ts or (lbl == "army ready" and not a.need_loot):
            continue
        cands.append((max(ts + buffer, t + min_gap), f"{lbl} finishes"))
    cands.append((t + max_gap, "max interval: collect + top up storages"))
    cands.sort(key=lambda c: c[0])
    night_end = window_end(cfg.get("night_hours"), t)
    by_hour, _, n = availability_profile(14)

    def likely(ts):
        ok, tot = by_hour.get(ts.hour, [0, 0])
        if window_end(cfg.get("night_hours"), ts):
            return "night window (good)"
        return f"{100 * ok / tot:.0f}% runnable historically" if tot else "unknown"

    print(json.dumps({
        "now": iso(t),
        "in_night_window": bool(night_end),
        "next_night_starts": None if night_end else iso(next_window_start(cfg.get("night_hours"), t)),
        "candidates": [{"at": iso(c[0]), "in": fmt_left(c[0] - t), "why": c[1], "availability": likely(c[0])}
                       for c in cands[:8]],
        "hint": "Pick a time a builder/lab is free or loot is needed AND the system can likely run then. "
                "If the best time is in a historically busy daytime hour, also set --opportunistic-after so an idle "
                "moment can be used early.",
    }, indent=2))


def cmd_stats(a):
    t = now()
    since = t - dt.timedelta(days=a.days)
    runs = [r for r in read_jsonl(LOGS / "runs.jsonl", since, key="started_at") if r.get("status") != "deferred"]
    deferred = [r for r in read_jsonl(LOGS / "runs.jsonl", since, key="deferred_at") if r.get("status") == "deferred"]
    attacks = read_jsonl(LOGS / "attacks.jsonl", since)
    upgrades = read_jsonl(LOGS / "upgrades.jsonl", since)
    research = read_jsonl(LOGS / "researchs.jsonl", since)
    walls = read_jsonl(LOGS / "walls.jsonl", since)
    snaps = read_jsonl(LOGS / "snapshots.jsonl", since)
    exps = read_jsonl(LOGS / "experiments.jsonl", since)

    def num(x):
        try:
            return float(str(x).replace(",", ""))
        except (TypeError, ValueError):
            return 0.0

    st = collections.Counter(r.get("status") for r in runs)
    print(f"== last {a.days} day(s) ==")
    print(f"runs: {len(runs)}  {dict(st)}  avg {sum(r.get('minutes') or 0 for r in runs) / max(len(runs), 1):.1f} min; deferred {len(deferred)}: "
          f"{dict(collections.Counter((r.get('reason') or '').split('(')[0].strip() for r in deferred).most_common(4))}")
    if attacks:
        g = [num((x.get("loot") or {}).get("gold")) for x in attacks]
        e = [num((x.get("loot") or {}).get("elixir")) for x in attacks]
        de = [num((x.get("loot") or {}).get("de")) for x in attacks]
        stars = [num(x.get("stars")) for x in attacks]
        nexts = [num(x.get("nexts")) for x in attacks]
        print(f"attacks: {len(attacks)}  avg loot gold {sum(g)/len(g):,.0f}  elixir {sum(e)/len(e):,.0f}  DE {sum(de)/len(de):,.0f}"
              f"  avg stars {sum(stars)/len(stars):.1f}  avg nexts {sum(nexts)/len(nexts):.1f}")
        wasted = [x for x in attacks if x.get("loot_wasted")]
        if wasted:
            print(f"  attacks with loot wasted to full storage: {len(wasted)}")
        strat = collections.defaultdict(list)
        for x in attacks:
            strat[x.get("strategy", "?")].append(num((x.get("loot") or {}).get("gold")) + num((x.get("loot") or {}).get("elixir")))
        for k, v in strat.items():
            print(f"  strategy {k!r}: {len(v)} attacks, avg gold+elixir {sum(v)/len(v):,.0f}")
    else:
        print("attacks: 0")
    print(f"upgrades started: {len(upgrades)}   research started: {len(research)}")
    today = t.date().isoformat()
    walls_today = sum(int(num(w.get("count", 1))) for w in walls if w["_t"].date().isoformat() == today)
    days_seen = len({w["_t"].date() for w in walls}) or 1
    print(f"walls: {sum(int(num(w.get('count', 1))) for w in walls)} segments ({walls_today} today, "
          f"~{sum(int(num(w.get('count', 1))) for w in walls) / days_seen:.1f}/active day)")
    if snaps:
        fills = []
        idle_poor = 0
        for s in snaps:
            for res in ("gold", "elixir"):
                cap = num((s.get("caps") or {}).get(res))
                if cap:
                    fills.append(num(s.get(res)) / cap)
            if num(s.get("builders_idle")) > 0 and s.get("blocked_by_loot"):
                idle_poor += 1
        if fills:
            print(f"storage fill at run start: avg {100*sum(fills)/len(fills):.0f}%  min {100*min(fills):.0f}%")
        print(f"runs where an idle builder had to wait for loot: {idle_poor}/{len(snaps)}  <- the number to drive to 0")
    if exps:
        print("experiments:")
        for x in exps[-5:]:
            print(f"  {x['_t'].strftime('%m-%d %H:%M')} {x.get('name', '?')}: {x.get('status', '')} {x.get('result', '')}")


def cmd_config(_):
    knobs, limits = game_knobs()
    cfg = full_config()
    tuning = load_json(MEMORY / "tuning.json", {}) or {}
    print(json.dumps({"knobs": knobs, "hard_limits": limits, "night_hours": cfg.get("night_hours"),
                      "tuned": {k: (v.get("why") if isinstance(v, dict) else "") for k, v in (tuning.get("knobs") or {}).items()}},
                     indent=2))


def cmd_tune(a):
    try:
        value = json.loads(a.value)
    except json.JSONDecodeError:
        value = a.value
    _, limits = game_knobs()
    for k, lim in LIMIT_FOR.items():
        if a.key == k and isinstance(value, (int, float)) and lim in limits and value > limits[lim]:
            print(f"note: {k} capped at hard limit {limits[lim]}")
            value = limits[lim]
    if a.key in limits:
        sys.exit(f"{a.key} is a hard limit set by the owner; you can't tune it")
    tuning = load_json(MEMORY / "tuning.json", {}) or {}
    knobs = tuning.setdefault("knobs", {})
    old = knobs.get(a.key, {}).get("value") if isinstance(knobs.get(a.key), dict) else knobs.get(a.key)
    knobs[a.key] = {"value": value, "why": a.why, "at": iso(now())}
    tuning["updated_at"] = iso(now())
    write_json(MEMORY / "tuning.json", tuning)
    with open(LOGS / "tuning.jsonl", "a") as f:
        f.write(json.dumps({"ts": iso(now()), "run_id": RUN_ID, "key": a.key, "old": old, "new": value, "why": a.why}) + "\n")
    print(f"tuned {a.key}: {old} -> {value}")


def cmd_log(a):
    if a.kind not in LOG_KINDS:
        sys.exit(f"kind must be one of {sorted(LOG_KINDS)}")
    try:
        payload = json.loads(a.payload)
    except json.JSONDecodeError as e:
        sys.exit(f"payload is not valid JSON: {e}")
    rec = {"ts": iso(now()), "run_id": RUN_ID, **payload}
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / f"{a.kind}s.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"logged {a.kind}")


def cmd_finish(a):
    if a.status not in VALID_STATUS:
        sys.exit(f"--status must be one of {sorted(VALID_STATUS)}")
    try:
        nxt = parse_when(a.next)
        opp = parse_when(a.opportunistic_after) if a.opportunistic_after else None
    except ValueError as e:
        sys.exit(str(e))
    if nxt <= now():
        sys.exit("--next must be in the future")
    for f in ("base.json", "tuning.json"):
        if (MEMORY / f).exists() and load_json(MEMORY / f) is None:
            sys.exit(f"memory/{f} is not valid JSON - fix it before finishing")
    result = {
        "run_id": RUN_ID,
        "status": a.status,
        "next_wake_at": iso(nxt),
        "reason": a.reason,
        "summary": a.summary,
        "opportunistic_after": iso(opp) if opp else None,
        "opportunistic_why": a.opportunistic_why or "",
        "finished_at": iso(now()),
    }
    write_json(RESULT_FILE, result)
    print("RUN RESULT WRITTEN:", json.dumps(result))
    print("You are done. Stop now and do not call any more tools.")


def main():
    p = argparse.ArgumentParser(prog="coc", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("now").set_defaults(fn=cmd_now)
    s = sub.add_parser("at"); s.add_argument("duration"); s.set_defaults(fn=cmd_at)
    sub.add_parser("timers").set_defaults(fn=cmd_timers)
    s = sub.add_parser("suggest-wake"); s.add_argument("--need-loot", action="store_true"); s.set_defaults(fn=cmd_suggest_wake)
    s = sub.add_parser("availability"); s.add_argument("--days", type=int, default=14); s.set_defaults(fn=cmd_availability)
    s = sub.add_parser("stats"); s.add_argument("--days", type=int, default=3); s.set_defaults(fn=cmd_stats)
    sub.add_parser("config").set_defaults(fn=cmd_config)
    s = sub.add_parser("tune"); s.add_argument("key"); s.add_argument("value"); s.add_argument("--why", required=True); s.set_defaults(fn=cmd_tune)
    s = sub.add_parser("log"); s.add_argument("kind"); s.add_argument("payload"); s.set_defaults(fn=cmd_log)
    s = sub.add_parser("finish")
    s.add_argument("--status", required=True)
    s.add_argument("--next", required=True, help="'+1h 30m' or ISO timestamp")
    s.add_argument("--reason", required=True)
    s.add_argument("--summary", required=True)
    s.add_argument("--opportunistic-after", default=None, help="earliest time an EARLY run would be useful if the owner is idle")
    s.add_argument("--opportunistic-why", default=None)
    s.set_defaults(fn=cmd_finish)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
