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
  direction
    coc direction                    the owner's direction: active strategy profile + their own notes
    coc config                       current game knobs (defaults + profile + your tuning, clamped to limits)
    coc today                        today's attacks / walls / runs against the owner's daily caps
  learning
    coc stats [--days 3]             runs, attacks, loot/attack, walls/day, storage fill, idle builders
    coc progress [--days 14]         day-by-day trend: builder/lab utilisation, upgrades, walls, loot, TH, trophies
    coc tune <key> <value> --why ".."   change a knob in memory/tuning.json (logged, scoped to the profile)
    coc experiment start <name> --hypothesis ".." [--metric loot|stars|destruction|nexts|trophies] [--strategy TAG]
    coc experiment status            the open experiment: metric since start vs the same number of attacks before
    coc experiment end --result keep|revert [--notes ".."]
    coc log <kind> '<json>'          kinds: attack upgrade research wall snapshot experiment event
  end of run
    coc finish --status ok --next "+2h10m" --reason "..." --summary "..."
               [--opportunistic-after "+40m" --opportunistic-why "army ready, storages 70%"]
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cocconf  # noqa: E402  (app/cocconf.py)

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
LIMIT_FOR = cocconf.LIMIT_FOR
METRICS = ("loot", "stars", "destruction", "nexts", "trophies")


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
    return cocconf.config()


def game_knobs(cfg: dict | None = None) -> tuple[dict, dict, dict]:
    """(knobs, limits, ignored): config 'game' (defaults + profile + owner) overlaid with memory/tuning.json,
    clamped to game_limits. Tuning made under a different profile is ignored (and returned in `ignored`),
    so switching profile gives that profile's starting values back."""
    cfg = cfg or full_config()
    profile = cfg.get("_profile")
    limits = {k: v for k, v in (cfg.get("game_limits") or {}).items() if not k.startswith("_")}
    knobs = {k: v for k, v in (cfg.get("game") or {}).items() if not k.startswith("_")}
    tuning = load_json(MEMORY / "tuning.json", {}) or {}
    ignored = {}
    for k, v in (tuning.get("knobs") or {}).items():
        if isinstance(v, dict) and v.get("profile") and v.get("profile") != profile:
            ignored[k] = v
            continue
        knobs[k] = v.get("value") if isinstance(v, dict) else v
    for k, lim in LIMIT_FOR.items():
        if k in knobs and lim in limits and isinstance(knobs[k], (int, float)):
            knobs[k] = min(knobs[k], limits[lim])
    return knobs, limits, ignored


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
    bb_attacks = [x for x in attacks if str(x.get("strategy", "")).startswith("bb")]
    attacks = [x for x in attacks if not str(x.get("strategy", "")).startswith("bb")]
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
        tro = [num(x.get("trophies")) for x in attacks if x.get("trophies") is not None]
        if tro:
            print(f"  trophies: {sum(tro):+.0f} over {len(tro)} logged attacks")
    else:
        print("attacks: 0")
    if bb_attacks:
        print(f"builder base attacks: {len(bb_attacks)}  avg stars {sum(num(x.get('stars')) for x in bb_attacks)/len(bb_attacks):.1f}")
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
            detail = x.get("hypothesis") if x.get("status") == "started" else (x.get("notes") or x.get("result") or "")
            print(f"  {x['_t'].strftime('%m-%d %H:%M')} {x.get('name', '?')}: {x.get('status', '')}  {detail}")


def _num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def cmd_progress(a):
    """Is the account actually getting better? One row per day."""
    t = now()
    since = (t - dt.timedelta(days=a.days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    base = load_json(MEMORY / "base.json", {}) or {}
    default_total = (base.get("builders") or {}).get("total")
    snaps = read_jsonl(LOGS / "snapshots.jsonl", since)
    per = collections.defaultdict(lambda: collections.defaultdict(float))
    for s in snaps:
        d = per[s["_t"].date()]
        d["snaps"] += 1
        total = _num(s.get("builders_total") or default_total)
        if total:
            d["busy_sum"] += max(0.0, 1 - _num(s.get("builders_idle")) / total)
            d["busy_n"] += 1
        if s.get("lab_idle") is not None:
            d["lab_busy"] += 0 if s.get("lab_idle") else 1
            d["lab_n"] += 1
        d["blocked"] += 1 if s.get("blocked_by_loot") else 0
        for res in ("gold", "elixir"):
            cap = _num((s.get("caps") or {}).get(res))
            if cap:
                d["fill_sum"] += _num(s.get(res)) / cap
                d["fill_n"] += 1
    for kind, key in (("upgrades", "upg"), ("researchs", "res")):
        for r in read_jsonl(LOGS / f"{kind}.jsonl", since):
            per[r["_t"].date()][key] += 1
    for w in read_jsonl(LOGS / "walls.jsonl", since):
        per[w["_t"].date()]["walls"] += _num(w.get("count", 1)) or 1
    for x in read_jsonl(LOGS / "attacks.jsonl", since):
        if str(x.get("strategy", "")).startswith("bb"):
            continue
        d = per[x["_t"].date()]
        d["att"] += 1
        d["loot"] += _num((x.get("loot") or {}).get("gold")) + _num((x.get("loot") or {}).get("elixir"))
        d["tro"] += _num(x.get("trophies"))

    def pct(sum_, n):
        return f"{100 * sum_ / n:3.0f}%" if n else "   -"

    print(f"== progress, last {a.days} day(s) ==   (builders/lab = share busy at run start; aim for 100%)")
    print("day         runs builders lab  blocked fill  upgrades research walls attacks avg_loot   trophies")
    for i in range(a.days):
        day = (since + dt.timedelta(days=i)).date()
        d = per.get(day)
        if not d:
            print(f"{day}  (no data)")
            continue
        avg = d["loot"] / d["att"] if d["att"] else 0
        print(f"{day}  {int(d['snaps']):>4} {pct(d['busy_sum'], d['busy_n']):>8} {pct(d['lab_busy'], d['lab_n']):>4} "
              f"{int(d['blocked']):>7} {pct(d['fill_sum'], d['fill_n']):>4} {int(d['upg']):>9} {int(d['res']):>8} "
              f"{int(d['walls']):>5} {int(d['att']):>7} {avg:>10,.0f} {d['tro']:>+9.0f}")
    th = [(s["_t"], s.get("town_hall")) for s in snaps if s.get("town_hall")]
    if len(th) >= 2 and th[0][1] != th[-1][1]:
        print(f"Town Hall: {th[0][1]} -> {th[-1][1]}")
    elif base.get("town_hall"):
        print(f"Town Hall: {base.get('town_hall')} (from memory/base.json)")
    tro = [(s.get("trophies")) for s in snaps if s.get("trophies") is not None]
    if len(tro) >= 2:
        print(f"Trophies at run start: {tro[0]} -> {tro[-1]}")
    if not snaps:
        print("(no snapshots yet: log one every run with `coc log snapshot`, including builders_total, town_hall, trophies)")


def _experiments():
    """(open_experiment_or_None, all_records)"""
    recs = read_jsonl(LOGS / "experiments.jsonl")
    open_ = None
    for r in recs:
        st = r.get("status")
        if st == "started":
            open_ = r
        elif st in ("ended", "kept", "reverted") and open_ and r.get("name") in (open_.get("name"), None):
            open_ = None
    return open_, recs


def _metric(x, metric):
    if metric == "loot":
        return _num((x.get("loot") or {}).get("gold")) + _num((x.get("loot") or {}).get("elixir"))
    return _num(x.get(metric))


def cmd_experiment(a):
    open_, _ = _experiments()
    path = LOGS / "experiments.jsonl"
    LOGS.mkdir(parents=True, exist_ok=True)
    if a.action == "start":
        if not a.name or not a.hypothesis:
            sys.exit("usage: coc experiment start <name> --hypothesis '...' [--metric loot] [--strategy TAG]")
        if open_:
            sys.exit(f"experiment {open_.get('name')!r} is still open (started {open_.get('ts')}). "
                     "One at a time: `coc experiment end --result keep|revert` first.")
        if a.metric not in METRICS:
            sys.exit(f"--metric must be one of {METRICS}")
        rec = {"ts": iso(now()), "run_id": RUN_ID, "name": a.name, "hypothesis": a.hypothesis, "metric": a.metric,
               "strategy": a.strategy, "status": "started", "profile": full_config().get("_profile"),
               "attacks_offset": len(read_jsonl(LOGS / "attacks.jsonl"))}  # position, not clock: ts has 1 s resolution
        with open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"experiment {a.name!r} started; metric={a.metric}" + (f", attacks tagged {a.strategy!r}" if a.strategy else ""))
        print("Tag the attacks it affects with that strategy name. Check with `coc experiment status`; aim for 5+ attacks before deciding.")
        return
    if not open_:
        print("no open experiment")
        return
    started = parse_ts(open_.get("ts"))
    metric = open_.get("metric") or "loot"
    all_attacks = read_jsonl(LOGS / "attacks.jsonl")
    off = open_.get("attacks_offset")
    if isinstance(off, int):
        before_all, after_all = all_attacks[:off], all_attacks[off:]
    else:  # experiments logged with `coc log experiment`
        before_all = [x for x in all_attacks if x["_t"] and x["_t"] < started]
        after_all = [x for x in all_attacks if x["_t"] and x["_t"] >= started]

    def home(xs):
        return [x for x in xs if not str(x.get("strategy", "")).startswith("bb")]
    after = home(after_all)
    if open_.get("strategy"):
        after = [x for x in after if x.get("strategy") == open_["strategy"]]
    before = home(before_all)[-max(len(after), 5):]

    def avg(xs):
        return sum(_metric(x, metric) for x in xs) / len(xs) if xs else None
    b, af = avg(before), avg(after)
    summary = {"name": open_.get("name"), "hypothesis": open_.get("hypothesis"), "metric": metric,
               "since": open_.get("ts"), "attacks_after": len(after), "avg_after": af,
               "attacks_before": len(before), "avg_before": b,
               "change_pct": round(100 * (af - b) / b, 1) if (af is not None and b) else None,
               "enough_data": len(after) >= 5}
    if a.action == "status":
        print(json.dumps(summary, indent=2))
        return
    if a.action == "end":
        if a.result not in ("keep", "revert"):
            sys.exit("--result keep|revert is required")
        rec = {"ts": iso(now()), "run_id": RUN_ID, "name": open_.get("name"),
               "status": "kept" if a.result == "keep" else "reverted", "result": a.result, "notes": a.notes or "",
               "measured": summary}
        with open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(json.dumps(rec, indent=2))
        print("Now write the result into memory/strategy.md (Open experiment + changelog).")


def cmd_config(_):
    cfg = full_config()
    knobs, limits, ignored = game_knobs(cfg)
    tuning = load_json(MEMORY / "tuning.json", {}) or {}
    strat = {k: v for k, v in (cfg.get("strategy") or {}).items() if not k.startswith("_")}
    out = {"profile": cfg.get("_profile"), "strategy": strat, "knobs": knobs, "hard_limits": limits,
           "night_hours": cfg.get("night_hours"),
           "tuned": {k: (v.get("why") if isinstance(v, dict) else "") for k, v in (tuning.get("knobs") or {}).items()
                     if k not in ignored}}
    if ignored:
        out["tuning_ignored_other_profile"] = {k: f"{v.get('value')} (tuned under {v.get('profile')})" for k, v in ignored.items()}
    if cfg.get("_profile_error"):
        out["profile_error"] = cfg["_profile_error"]
    print(json.dumps(out, indent=2))


def cmd_direction(_):
    cfg = full_config()
    name = cfg.get("_profile")
    prof = cocconf.load_profile(name)
    if not prof:
        print(f"WARNING: {cfg.get('_profile_error')}. Falling back to {cocconf.DEFAULT_PROFILE}.\n")
        prof = cocconf.load_profile(cocconf.DEFAULT_PROFILE) or {"direction": "", "summary": ""}
    print(prof["direction"].rstrip())
    strat = cfg.get("strategy") or {}
    style = strat.get("attack_style") or "auto"
    print(f"\n## Attack style\n- `{style}`" + (" (your choice: pick from app/knowledge/attacks.md for this army)" if style == "auto"
                                               else " (the owner chose this recipe in app/knowledge/attacks.md; adapt details, keep the recipe)"))
    notes = strat.get("notes") or []
    if isinstance(notes, str):
        notes = [notes]
    extra = COC_HOME / "direction.md"
    if notes or extra.exists():
        print("\n## The owner's own notes (these override the profile where they conflict)")
        for n in notes:
            print(f"- {n}")
        if extra.exists():
            print(extra.read_text().rstrip())
    flags = {k: v for k, v in (cfg.get("game_limits") or {}).items() if isinstance(v, bool)}
    print("\n## Switches the owner set (game_limits)\n" + ", ".join(f"{k}={'on' if v else 'off'}" for k, v in flags.items()))


def _today_counts():
    t = now()
    start = t.replace(hour=0, minute=0, second=0, microsecond=0)
    attacks = read_jsonl(LOGS / "attacks.jsonl", start)
    home = [x for x in attacks if not str(x.get("strategy", "")).startswith("bb")]
    walls = read_jsonl(LOGS / "walls.jsonl", start)
    runs = [r for r in read_jsonl(LOGS / "runs.jsonl", start, key="started_at") if r.get("status") != "deferred"]

    def n(x):
        try:
            return int(float(x))
        except (TypeError, ValueError):
            return 1
    return {"attacks_home": len(home), "attacks_builder_base": len(attacks) - len(home),
            "walls": sum(n(w.get("count", 1)) for w in walls), "runs": len(runs)}


def cmd_today(_):
    cfg = full_config()
    knobs, limits, _ = game_knobs(cfg)
    c = _today_counts()
    cap = limits.get("max_attacks_per_day")
    out = {**c, "max_attacks_per_day": cap,
           "attacks_left_today": (max(cap - c["attacks_home"], 0) if isinstance(cap, (int, float)) else None),
           "walls_per_day_target": knobs.get("walls_per_day_target"),
           "walls_left_for_target": max((knobs.get("walls_per_day_target") or 0) - c["walls"], 0),
           "max_runs_per_day": cfg.get("max_runs_per_day")}
    print(json.dumps(out, indent=2))


def cmd_tune(a):
    try:
        value = json.loads(a.value)
    except json.JSONDecodeError:
        value = a.value
    cfg = full_config()
    _, limits, _ = game_knobs(cfg)
    for k, lim in LIMIT_FOR.items():
        if a.key == k and isinstance(value, (int, float)) and lim in limits and value > limits[lim]:
            print(f"note: {k} capped at hard limit {limits[lim]}")
            value = limits[lim]
    if a.key in limits:
        sys.exit(f"{a.key} is a hard limit set by the owner; you can't tune it")
    tuning = load_json(MEMORY / "tuning.json", {}) or {}
    knobs = tuning.setdefault("knobs", {})
    old = knobs.get(a.key, {}).get("value") if isinstance(knobs.get(a.key), dict) else knobs.get(a.key)
    knobs[a.key] = {"value": value, "why": a.why, "at": iso(now()), "profile": cfg.get("_profile")}
    tuning["updated_at"] = iso(now())
    write_json(MEMORY / "tuning.json", tuning)
    with open(LOGS / "tuning.jsonl", "a") as f:
        f.write(json.dumps({"ts": iso(now()), "run_id": RUN_ID, "key": a.key, "old": old, "new": value, "why": a.why,
                            "profile": cfg.get("_profile")}) + "\n")
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
    if a.kind == "attack" and not str(payload.get("strategy", "")).startswith("bb"):
        _, limits, _ = game_knobs()
        cap = limits.get("max_attacks_per_day")
        done = _today_counts()["attacks_home"]
        if isinstance(cap, (int, float)) and done >= cap:
            print(f"DAILY ATTACK CAP REACHED ({done}/{cap}, owner's max_attacks_per_day). No more home-village attacks today.")


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
    sub.add_parser("direction").set_defaults(fn=cmd_direction)
    sub.add_parser("today").set_defaults(fn=cmd_today)
    s = sub.add_parser("progress"); s.add_argument("--days", type=int, default=14); s.set_defaults(fn=cmd_progress)
    s = sub.add_parser("experiment")
    s.add_argument("action", choices=["start", "status", "end"])
    s.add_argument("name", nargs="?")
    s.add_argument("--hypothesis")
    s.add_argument("--metric", default="loot")
    s.add_argument("--strategy", default=None, help="attack strategy tag the experiment applies to")
    s.add_argument("--result", choices=["keep", "revert"])
    s.add_argument("--notes")
    s.set_defaults(fn=cmd_experiment)
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
