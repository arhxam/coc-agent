#!/usr/bin/env python3
"""coc-agent scheduler.

A small, reliable loop. The game decisions (what to upgrade, when to attack,
when to come back) belong to the Claude agent. This process only knows about
the real world: is the Mac free, are we at home, is the iPhone nearby, is it
night. It decides whether a run can start right now:

    loop every 20s:
        sample presence (home network, iPhone nearby, Mac idle/locked) -> logs/presence.jsonl
        night window + at home      -> hold `caffeinate` so the Mac never sleeps/locks
        paused?                     -> idle
        due (now >= next_wake_at)?  -> preflight -> run, or push out ~30 min and log why
        not due, but a GOLDEN moment (home + iPhone nearby + you idle for a while,
                   and the agent said an early run is worth it after `opportunistic_after`)
                                    -> opportunistic run
        after a run: read state/run_result.json, clamp the agent's next_wake_at, save it

    python3 scheduler.py daemon       # run the loop (used by cocctl start / launchd)
    python3 scheduler.py run-once     # one run right now (skips the idle check)
    python3 scheduler.py preflight    # print the preflight verdict
    python3 scheduler.py presence     # print what the Mac can sense right now
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cocconf  # noqa: E402

COC_HOME = Path(os.environ.get("COC_HOME", Path.home() / ".coc-agent"))
APP = COC_HOME / "app"
STATE = COC_HOME / "state"
LOGS = COC_HOME / "logs"
SESSIONS = LOGS / "sessions"
SCHEDULE_FILE = STATE / "schedule.json"
RESULT_FILE = STATE / "run_result.json"
CURRENT_RUN = STATE / "current_run.json"
RUN_LOCK = STATE / "run.lock"
HEARTBEAT = STATE / "scheduler.json"
PAUSED_FLAG = STATE / "PAUSED"
RUN_NOW_FLAG = STATE / "RUN_NOW"
CU_LOCK = Path(os.environ.get("COC_CU_LOCK", Path.home() / ".claude" / "computer-use.lock"))

TICK_SECONDS = 20
_child: subprocess.Popen | None = None


# ---------------------------------------------------------------- utilities
def now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def iso(t: dt.datetime) -> str:
    return t.astimezone().isoformat(timespec="seconds")


def parse_ts(v):
    if not v:
        return None
    try:
        t = dt.datetime.fromisoformat(str(v))
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
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)


def append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def log(msg: str) -> None:
    line = f"{now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / "scheduler.log", "a") as f:
        f.write(line + "\n")


def config() -> dict:
    """defaults <- strategy profile <- owner's config.json (see cocconf.py)."""
    return cocconf.config()


def notify(title: str, message: str) -> None:
    if not config().get("notify", True):
        return
    msg = message.replace('"', "'")[:220]
    subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "{title}"'],
                   capture_output=True, timeout=10)


def pid_alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, ValueError, TypeError):
        return False
    except PermissionError:
        return True


def find_claude(cfg: dict) -> str | None:
    for c in (cfg.get("claude_bin"), shutil.which("claude"),
              str(Path.home() / ".local/bin/claude"), "/opt/homebrew/bin/claude", "/usr/local/bin/claude"):
        if c and Path(c).exists():
            return c
    return None


# ---------------------------------------------------------------- schedule
def get_schedule() -> dict:
    s = load_json(SCHEDULE_FILE)
    if not s or not parse_ts(s.get("next_wake_at")):
        s = {"next_wake_at": iso(now()), "reason": "first start", "source": "scheduler",
             "consecutive_failures": 0}
        write_json(SCHEDULE_FILE, s)
    return s


def set_schedule(when: dt.datetime, reason: str, source: str, **extra) -> dict:
    s = get_schedule()
    s.update({"next_wake_at": iso(when), "reason": reason, "source": source,
              "updated_at": iso(now()), **extra})
    write_json(SCHEDULE_FILE, s)
    log(f"next wake {when.strftime('%a %H:%M')} ({source}): {reason}")
    return s


# ---------------------------------------------------------------- preflight
def mac_idle_seconds() -> float | None:
    try:
        out = subprocess.run(["ioreg", "-c", "IOHIDSystem"], capture_output=True, text=True, timeout=10).stdout
        m = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', out)
        return int(m.group(1)) / 1e9 if m else None
    except Exception:
        return None


def screen_locked() -> bool:
    try:
        out = subprocess.run(["ioreg", "-n", "Root", "-d1", "-a"], capture_output=True, text=True, timeout=10).stdout
        m = re.search(r"<key>CGSSessionScreenIsLocked</key>\s*<(true|false)/>", out)
        return bool(m and m.group(1) == "true")
    except Exception:
        return False


def lid_closed() -> bool:
    try:
        out = subprocess.run(["ioreg", "-r", "-k", "AppleClamshellState", "-d", "4"],
                             capture_output=True, text=True, timeout=10).stdout
        return '"AppleClamshellState" = Yes' in out
    except Exception:
        return False


def battery() -> tuple[int | None, bool]:
    """(percent, on_ac_power)"""
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=10).stdout
        pct = re.search(r"(\d+)%", out)
        return (int(pct.group(1)) if pct else None, "AC Power" in out)
    except Exception:
        return (None, True)


def norm_mac(mac: str) -> str:
    return ":".join(p.zfill(2) for p in mac.strip().lower().split(":")) if mac else ""


def default_gateway_ip() -> str | None:
    try:
        out = subprocess.run(["route", "-n", "get", "default"], capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"gateway:\s*([\d.]+)", out)
        return m.group(1) if m else None
    except Exception:
        return None


def gateway_mac() -> str | None:
    """MAC of the default router: a location fingerprint that needs no Location permission
    (macOS redacts the Wi-Fi SSID for command-line tools)."""
    try:
        out = subprocess.run(["route", "-n", "get", "default"], capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"gateway:\s*([\d.]+)", out)
        if not m:
            return None
        arp = subprocess.run(["arp", "-n", m.group(1)], capture_output=True, text=True, timeout=5).stdout
        mm = re.search(r" at ([0-9a-fA-F:]+) ", arp)
        return norm_mac(mm.group(1)) if mm else None
    except Exception:
        return None


def iphone_nearby(address: str) -> bool | None:
    """True if the paired iPhone is connected or has a recent Bluetooth RSSI, False if it is
    paired but not seen, None if unknown/not configured."""
    if not address:
        return None
    try:
        out = subprocess.run(["system_profiler", "SPBluetoothDataType", "-json"],
                             capture_output=True, text=True, timeout=20).stdout
        data = json.loads(out)["SPBluetoothDataType"][0]
    except Exception:
        return None
    want = address.strip().lower()
    for section, devices in data.items():
        if not isinstance(devices, list):
            continue
        for dev in devices:
            for _name, info in dev.items():
                if str(info.get("device_address", "")).lower() == want:
                    return section == "device_connected" or "device_rssi" in info
    return False


def presence(cfg: dict) -> dict:
    pc = cfg.get("presence") or {}
    gw = gateway_mac()
    homes = {norm_mac(m) for m in pc.get("home_gateway_macs") or []}
    at_home = (gw in homes) if (homes and gw) else (False if homes else None)
    idle = mac_idle_seconds()
    t = now()
    return {
        "ts": iso(t),
        "at_home": at_home,
        "iphone_nearby": iphone_nearby(pc.get("iphone_bt_address", "")) if pc.get("enabled", True) else None,
        "mac_idle_s": int(idle) if idle is not None else None,
        "screen_locked": screen_locked(),
        "night": in_window(cfg.get("night_hours") or [], t) is not None,
    }


def in_window(windows, t: dt.datetime) -> dt.datetime | None:
    """If t is inside one of [["HH:MM","HH:MM"], ...], return when that window ends."""
    for start_s, end_s in windows or []:
        sh, sm = map(int, start_s.split(":"))
        eh, em = map(int, end_s.split(":"))
        start = t.replace(hour=sh, minute=sm, second=0, microsecond=0)
        end = t.replace(hour=eh, minute=em, second=0, microsecond=0)
        if start <= end:
            if start <= t < end:
                return end
        else:  # crosses midnight
            if t >= start:
                return end + dt.timedelta(days=1)
            if t < end:
                return end
    return None


def in_quiet_hours(cfg: dict, t: dt.datetime) -> dt.datetime | None:
    """If t is inside a quiet window, return when that window ends."""
    return in_window(cfg.get("quiet_hours"), t)


def runs_today() -> int:
    today = now().date().isoformat()
    n = 0
    try:
        for line in open(LOGS / "runs.jsonl"):
            if line.startswith("{") and f'"started_at": "{today}' in line:
                n += 1
    except FileNotFoundError:
        pass
    return n


def preflight(cfg: dict, manual: bool = False) -> tuple[bool, str, dt.timedelta]:
    """(ok, reason, defer_by)."""
    t = now()
    d = lambda k: dt.timedelta(minutes=cfg.get(k, cfg.get("defer_minutes", 30)))

    if not find_claude(cfg):
        return False, "claude CLI not found (set claude_bin in config.json)", dt.timedelta(hours=1)
    if not shutil.which("expect"):
        return False, "expect not found", dt.timedelta(hours=1)
    if RUN_LOCK.exists() and pid_alive((load_json(RUN_LOCK, {}) or {}).get("pid")):
        return False, "a coc-agent run is already in progress", dt.timedelta(minutes=5)
    if not manual:
        q = in_quiet_hours(cfg, t)
        if q:
            return False, f"quiet hours until {q.strftime('%H:%M')}", q - t
        if runs_today() >= cfg.get("max_runs_per_day", 30):
            tomorrow = (t + dt.timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
            return False, "daily run cap reached", tomorrow - t
    # Real-world blockers: collect ALL of them so the log/notification says everything that's wrong.
    blockers: list[tuple[str, dt.timedelta]] = []
    if lid_closed():
        blockers.append(("MacBook lid is closed (computer use needs the screen open)", d("defer_minutes")))
    if screen_locked():
        blockers.append(("Mac screen is locked (computer use needs an unlocked session)", d("defer_minutes")))
    cu = load_json(CU_LOCK, {}) or {}
    if cu.get("pid") and pid_alive(cu["pid"]):
        blockers.append((f"another Claude session holds computer use (pid {cu['pid']}; /exit it)", d("defer_minutes_cu_lock_busy")))
    pc = cfg.get("presence") or {}
    if not manual and pc.get("enabled", True):
        p = presence(cfg)
        if pc.get("require_home", True) and p["at_home"] is False:
            gw = default_gateway_ip() or "none"
            where = " - looks like the iPhone's Personal Hotspot" if gw.startswith(("172.20.10.", "192.0.0.")) else ""
            blockers.append((f"not on home Wi-Fi (gateway {gw}{where})", d("defer_minutes")))
        if pc.get("require_iphone_nearby", False) and p["iphone_nearby"] is False:
            blockers.append(("iPhone not seen nearby over Bluetooth", d("defer_minutes")))
    if not manual and not cfg.get("skip_idle_check"):
        idle = mac_idle_seconds()
        need = cfg.get("mac_idle_required_seconds", 300)
        if idle is not None and idle < need:
            blockers.append((f"you are using the Mac (idle {int(idle)}s < {need}s)", d("defer_minutes_mac_busy")))
    pct, ac = battery()
    if pct is not None and not ac and pct < cfg.get("min_battery_percent", 20):
        blockers.append((f"battery {pct}% and not charging", d("defer_minutes_low_battery")))
    if blockers:
        return False, "; ".join(b[0] for b in blockers), min(b[1] for b in blockers)
    return True, "ok", dt.timedelta(0)


# ---------------------------------------------------------------- one run
def first_run() -> bool:
    """No onboarding survey yet: memory/base.json has no Town Hall level."""
    base = load_json(COC_HOME / "memory" / "base.json", {}) or {}
    return not base.get("town_hall")


def weekly_review_due(cfg: dict, sched: dict, t: dt.datetime) -> bool:
    last = parse_ts(sched.get("last_weekly_review_at"))
    if last and t - last < dt.timedelta(days=6):
        return False
    day = str(cfg.get("weekly_review_weekday") or "Sunday").lower()
    return t.strftime("%A").lower() == day or (last is not None and t - last >= dt.timedelta(days=8))


def build_prompt(run_id: str, trigger: str, sched: dict, review: bool, pres: dict | None,
                 weekly: bool = False) -> str:
    t = now()
    cfg = config()
    night = in_window(cfg.get("night_hours") or [], t)
    profile = cfg.get("_profile")
    parts = [
        f"coc-agent run {run_id}. Local time {iso(t)} ({t.strftime('%A')}). Trigger: {trigger}.",
        f"Strategy profile: {profile} (`./bin/coc direction` prints the owner's direction).",
        f"Plan you left for this wake-up: {sched.get('reason', 'none')}.",
        f"Night window: {'YES, until ' + night.strftime('%H:%M') + ' (owner asleep: prime time to farm and fill storages)' if night else 'no'}.",
    ]
    if pres:
        parts.append(f"Presence: at_home={pres.get('at_home')}, iphone_nearby={pres.get('iphone_nearby')}, mac_idle={pres.get('mac_idle_s')}s.")
    if first_run():
        parts.append("FIRST RUN on this account: do the ONBOARDING SURVEY from CLAUDE.md before anything else "
                     "(Town Hall, builders, army, heroes; write base.json, upgrade_priorities.md, attack_playbook.md, strategy.md).")
    if sched.get("last_profile") and sched.get("last_profile") != profile:
        parts.append(f"The owner CHANGED the strategy profile from {sched['last_profile']} to {profile}: "
                     "read `./bin/coc direction` and re-derive memory/strategy.md and upgrade_priorities.md from it this run.")
    if weekly:
        parts.append("WEEKLY REVIEW is due: do it from CLAUDE.md (coc progress --days 7, Town Hall decision, prune memory).")
    elif review:
        parts.append("This is the first run of the day: do the DAILY REVIEW from CLAUDE.md (stats, availability, rewrite memory/strategy.md) before or after playing, whichever fits the time.")
    parts.append("Work through CLAUDE.md: read memory/strategy.md first, play, learn, update memory, then `./bin/coc finish ...` and stop.")
    return " ".join(parts)


def clean_env() -> dict:
    """Never leak the parent Claude Code session's markers into the child session."""
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("CLAUDE_CODE_") or k in ("CLAUDECODE", "CLAUDE_PID", "AI_AGENT",
                                                          "CLAUDE_AGENT_SDK_VERSION", "CLAUDE_EFFORT"))}
    extra = [str(Path.home() / ".local/bin"), "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    env["PATH"] = ":".join(dict.fromkeys(env.get("PATH", "").split(":") + extra))
    env.setdefault("TERM", "xterm-256color")
    env["COC_HOME"] = str(COC_HOME)
    return env


def run_session(trigger: str, attach: bool = False) -> dict:
    global _child
    cfg = config()
    sched = get_schedule()
    review = sched.get("last_review_date") != now().date().isoformat() and now().hour >= cfg.get("daily_review_after_hour", 4)
    weekly = review and weekly_review_due(cfg, sched, now())
    try:
        pres = presence(cfg)
    except Exception:
        pres = None
    claude = find_claude(cfg)
    started = now()
    run_id = started.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    SESSIONS.mkdir(parents=True, exist_ok=True)
    transcript = SESSIONS / f"{run_id}.tty.log"
    events = SESSIONS / f"{run_id}.events.log"

    RESULT_FILE.unlink(missing_ok=True)
    write_json(RUN_LOCK, {"pid": os.getpid(), "run_id": run_id, "started_at": iso(started)})
    write_json(CURRENT_RUN, {"run_id": run_id, "started_at": iso(started), "trigger": trigger})

    cmd = [claude, "--permission-mode", cfg.get("permission_mode", "dontAsk")]
    if cfg.get("model"):
        cmd += ["--model", cfg["model"]]
    if cfg.get("effort"):
        cmd += ["--effort", cfg["effort"]]
    cmd.append(build_prompt(run_id, trigger, sched, review, pres, weekly))

    env = clean_env()
    env.update({
        "COC_RUN_ID": run_id,
        "COC_RESULT_FILE": str(RESULT_FILE),
        "COC_TRANSCRIPT": str(transcript),
        "COC_EVENTS": str(events),
        "COC_MAX_SECONDS": str(int(cfg.get("max_run_minutes", 25) * 60)),
        "COC_STALL_SECONDS": str(int(cfg.get("stall_seconds", 300))),
        "COC_AUTO_APPROVE": "1" if cfg.get("auto_approve_app_access", True) else "0",
        "COC_APPROVE_KEYS": cfg.get("approve_keys", "DOWN,ENTER"),
        "COC_ATTACH": "1" if attach else "0",
    })

    log(f"run {run_id} starting ({trigger})")
    full = ["caffeinate", "-dimsu", "expect", str(APP / "run_session.exp"), *cmd]
    hard_limit = cfg.get("max_run_minutes", 25) * 60 + 180
    rc = None
    try:
        _child = subprocess.Popen(full, cwd=COC_HOME, env=env, start_new_session=True,
                                  stdout=None if attach else subprocess.DEVNULL,
                                  stderr=None if attach else subprocess.DEVNULL)
        rc = _child.wait(timeout=hard_limit)
    except subprocess.TimeoutExpired:
        log(f"run {run_id}: hard limit hit, killing session")
        os.killpg(_child.pid, signal.SIGTERM)
        time.sleep(3)
        try:
            os.killpg(_child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        rc = -1
    finally:
        _child = None
        RUN_LOCK.unlink(missing_ok=True)
        CURRENT_RUN.unlink(missing_ok=True)

    ended = now()
    result = load_json(RESULT_FILE)
    outcome = {0: "done", 10: "timeout", 11: "stalled", 12: "exited-without-result"}.get(rc, f"exit-{rc}")
    rec = {"run_id": run_id, "trigger": trigger, "started_at": iso(started), "ended_at": iso(ended),
           "minutes": round((ended - started).total_seconds() / 60, 1), "driver_outcome": outcome,
           "status": (result or {}).get("status", "no_result"),
           "summary": (result or {}).get("summary", ""),
           "agent_next_wake_at": (result or {}).get("next_wake_at"),
           "agent_reason": (result or {}).get("reason", "")}
    append_jsonl(LOGS / "runs.jsonl", rec)
    log(f"run {run_id} ended: {outcome}, status={rec['status']}, {rec['minutes']} min")
    if result and result.get("status") == "ok":
        s = get_schedule()
        s["last_profile"] = cfg.get("_profile")
        if review:
            s["last_review_date"] = now().date().isoformat()
        if weekly:
            s["last_weekly_review_at"] = iso(now())
        write_json(SCHEDULE_FILE, s)
    apply_result(result, run_id)
    return rec


def apply_result(result: dict | None, run_id: str) -> None:
    cfg = config()
    t = now()
    sched = get_schedule()
    fails = sched.get("consecutive_failures", 0)
    lo = t + dt.timedelta(minutes=cfg.get("min_interval_minutes", 15))
    hi = t + dt.timedelta(minutes=cfg.get("max_interval_minutes", 360))
    defer = dt.timedelta(minutes=cfg.get("defer_minutes", 30))

    s0 = get_schedule(); s0["last_run_ended_at"] = iso(t); s0["opportunistic_after"] = None; write_json(SCHEDULE_FILE, s0)
    if not result or result.get("run_id") not in (run_id, None):
        fails += 1
        backoff = min(defer * (2 ** (fails - 1)), dt.timedelta(hours=4))
        set_schedule(t + backoff, f"run {run_id} produced no result (failure #{fails}); backing off",
                     "scheduler", consecutive_failures=fails)
        if fails >= 3:
            notify("coc-agent needs a look", f"{fails} runs in a row failed. Check: cocctl logs")
        return

    status = result.get("status")
    nxt = parse_ts(result.get("next_wake_at")) or (t + defer)
    reason = result.get("reason") or status
    if status == "phone_in_use":  # owner has the phone: honor the agent's retry, within 10 min..2 h
        nxt = min(max(nxt, t + dt.timedelta(minutes=10)), t + dt.timedelta(hours=2))
    clamped = min(max(nxt, lo), hi)
    if clamped != nxt:
        reason += f" (clamped from {nxt.strftime('%H:%M')})"
    opp = parse_ts(result.get("opportunistic_after"))
    set_schedule(clamped, reason, "agent", consecutive_failures=0 if status in ("ok", "phone_in_use") else fails + 1,
                 last_status=status, last_summary=result.get("summary", ""),
                 opportunistic_after=iso(opp) if opp and opp < clamped else None,
                 opportunistic_why=result.get("opportunistic_why", ""))
    if status == "needs_human":
        notify("coc-agent needs you", result.get("summary") or reason)
    elif status == "ok" and cfg.get("notify", True):
        notify("coc-agent run done", f"{result.get('summary', '')[:150]}  Next: {clamped.strftime('%H:%M')}")


# ---------------------------------------------------------------- daemon
def heartbeat(state: str, extra: dict | None = None) -> None:
    write_json(HEARTBEAT, {"pid": os.getpid(), "state": state, "at": iso(now()), **(extra or {})})


def _on_term(signum, _frame):
    log(f"scheduler stopping (signal {signum})")
    if _child and _child.poll() is None:
        try:
            os.killpg(_child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if _caffeinate and _caffeinate.poll() is None:
        _caffeinate.terminate()
    RUN_LOCK.unlink(missing_ok=True)
    HEARTBEAT.unlink(missing_ok=True)
    sys.exit(0)


_caffeinate: subprocess.Popen | None = None


def night_keep_awake(cfg: dict, pres: dict) -> None:
    """During the night window at home, hold `caffeinate -di` so the display never sleeps and the
    screen never auto-locks (computer use cannot act on a locked screen)."""
    global _caffeinate
    want = bool(cfg.get("keep_awake_at_night", True) and in_window(cfg.get("night_hours") or [], now())
                and pres.get("at_home") is not False and not pres.get("screen_locked"))
    running = _caffeinate is not None and _caffeinate.poll() is None
    if want and not running:
        _caffeinate = subprocess.Popen(["caffeinate", "-dimsu"])
        log("night window: keeping the Mac awake (caffeinate)")
    elif not want and running:
        _caffeinate.terminate()
        _caffeinate = None
        log("night window over: released caffeinate")


def golden_moment(cfg: dict, sched: dict, pres: dict) -> str | None:
    """An early, unplanned run is worth it when the agent said so (opportunistic_after) AND the
    real world is ideal: at home, iPhone nearby, owner away from the Mac for a while."""
    oc = cfg.get("opportunistic") or {}
    if not oc.get("enabled", True) or PAUSED_FLAG.exists():
        return None
    after = parse_ts(sched.get("opportunistic_after"))
    t = now()
    if not after or t < after:
        return None
    last = parse_ts(sched.get("last_run_ended_at"))
    if last and (t - last) < dt.timedelta(minutes=oc.get("min_gap_minutes", 45)):
        return None
    if not pres or pres.get("at_home") is False or pres.get("iphone_nearby") is False or pres.get("screen_locked"):
        return None
    idle = mac_idle_seconds() or 0
    if idle < oc.get("min_idle_minutes", 20) * 60:
        return None
    return f"idle {int(idle // 60)}m at home; agent: {sched.get('opportunistic_why') or 'early run useful'}"


def daemon() -> None:
    for d in (STATE, LOGS, SESSIONS):
        d.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, _on_term)
    signal.signal(signal.SIGINT, _on_term)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    log(f"scheduler started (pid {os.getpid()}, home {COC_HOME})")
    get_schedule()
    last_sample = 0.0
    last_opp_block = None
    pres: dict = {}
    while True:
        cfg = config()
        sched = get_schedule()
        t = now()
        manual = RUN_NOW_FLAG.exists()
        if time.time() - last_sample >= cfg.get("presence_sample_minutes", 5) * 60:
            try:
                pres = presence(cfg)
                append_jsonl(LOGS / "presence.jsonl", pres)
            except Exception as e:
                log(f"presence sample failed: {e!r}")
            last_sample = time.time()
        night_keep_awake(cfg, pres)
        if PAUSED_FLAG.exists() and not manual:
            heartbeat("paused", {"next_wake_at": sched["next_wake_at"]})
            time.sleep(TICK_SECONDS)
            continue
        due = parse_ts(sched["next_wake_at"]) <= t
        opp = None if (due or manual) else golden_moment(cfg, sched, pres)
        if not (due or manual or opp):
            heartbeat("waiting", {"next_wake_at": sched["next_wake_at"], "reason": sched.get("reason"),
                                  "opportunistic_after": sched.get("opportunistic_after")})
            time.sleep(TICK_SECONDS)
            continue
        if opp:
            ok, why, _ = preflight(cfg)
            if not ok:
                if why != last_opp_block:
                    log(f"golden moment skipped: {why}")
                last_opp_block = why
                time.sleep(TICK_SECONDS)
                continue
            last_opp_block = None
            log(f"golden moment: {opp}")
            heartbeat("running")
            try:
                run_session(f"opportunistic ({opp})")
            except Exception as e:
                log(f"run crashed: {e!r}")
            continue
        ok, why, defer_by = preflight(cfg, manual=manual)
        if not ok:
            if manual:
                log(f"manual run blocked: {why}")
                RUN_NOW_FLAG.unlink(missing_ok=True)
            else:
                append_jsonl(LOGS / "runs.jsonl", {"started_at": None, "deferred_at": iso(t), "status": "deferred", "reason": why})
                blocked_since = parse_ts(sched.get("blocked_since")) or t
                extra = {"blocked_since": iso(blocked_since)}
                hours = (t - blocked_since).total_seconds() / 3600
                last_n = parse_ts(sched.get("blocked_notified_at"))
                if hours >= cfg.get("notify_blocked_after_hours", 2) and (not last_n or t - last_n >= dt.timedelta(hours=3)):
                    notify("coc-agent is stuck", f"No run for {hours:.0f}h: {why}")
                    log(f"notified: blocked {hours:.1f}h")
                    extra["blocked_notified_at"] = iso(t)
                set_schedule(t + defer_by, f"deferred: {why}", "preflight",
                             consecutive_failures=sched.get("consecutive_failures", 0), **extra)
            continue
        RUN_NOW_FLAG.unlink(missing_ok=True)
        s_ = get_schedule(); s_.pop("blocked_since", None); s_.pop("blocked_notified_at", None); write_json(SCHEDULE_FILE, s_)
        heartbeat("running")
        try:
            run_session("manual" if manual else "scheduled")
        except Exception as e:  # never let the daemon die
            log(f"run crashed: {e!r}")
            set_schedule(now() + dt.timedelta(minutes=cfg.get("defer_minutes", 30)), f"driver error: {e!r}", "scheduler")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "daemon"
    if cmd == "daemon":
        daemon()
    elif cmd == "run-once":
        attach = "--attach" in sys.argv
        ok, why, _ = preflight(config(), manual=True)
        if not ok:
            sys.exit(f"cannot run now: {why}")
        rec = run_session("manual", attach=attach)
        print(json.dumps(rec, indent=2))
    elif cmd == "preflight":
        ok, why, d = preflight(config())
        print(json.dumps({"ok": ok, "reason": why, "defer_minutes": round(d.total_seconds() / 60),
                          "mac_idle_seconds": mac_idle_seconds(), "screen_locked": screen_locked(),
                          "battery": battery()}, indent=2))
    elif cmd == "presence":
        print(json.dumps({**presence(config()), "gateway_mac": gateway_mac()}, indent=2))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
