<p align="center">
  <img src="docs/images/banner.png" alt="coc-agent: Claude plays Clash of Clans on my iPhone while I sleep" width="100%">
</p>

<p align="center">
  <b>An autonomous Clash of Clans agent built on Claude Code computer use and macOS iPhone Mirroring.</b><br>
  It farms loot, keeps every builder busy, upgrades walls from surplus, runs at night or when you're away,<br>
  and rewrites its own strategy as it learns.
</p>

<p align="center">
  <img alt="macOS 15+" src="https://img.shields.io/badge/macOS-15%2B-black?logo=apple">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-computer%20use-d97757">
  <img alt="Python 3" src="https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white">
  <img alt="No dependencies" src="https://img.shields.io/badge/dependencies-none-brightgreen">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue">
</p>

> [!WARNING]
> **Unofficial research project, for educational purposes only.** coc-agent is an experiment in what an AI agent can do with computer use. It is not a product, a service or a cheat tool, and it is not affiliated with, endorsed by or sponsored by Supercell, Anthropic or Apple.
>
> **Running it breaks Supercell's [Terms of Service](https://supercell.com/en/terms-of-service/), which forbid bots and automation. Your account can be suspended or permanently banned.** Only run it on an account you are prepared to lose. You alone are responsible for how you use it. See the [full disclaimer](#disclaimer).

<p align="center"><img src="docs/images/hero.jpg" alt="Real screenshot: Claude attacking with Electro Dragons through iPhone Mirroring, with its own narration" width="100%"></p>

---

## What it does

There's no game API, no memory reading and no injected code. Claude **looks at the screen and taps**, the way you would, through the iPhone Mirroring window on your Mac.

- **Banks loot.** It keeps storages near full so the moment a builder or the lab frees up, the next upgrade starts. Its #1 metric is *"a builder never waits for loot."*
- **Walls as an overflow valve.** It upgrades walls only with surplus above a reserve, a few per day.
- **Schedules around your life.** It does most of its work in a night window, and during the day only when you're home, the Mac is idle and the phone is locked nearby. **Claude picks its own next wake-up time** ("Builder 2 frees at 03:10, wake then").
- **Plays the Builder Base too** (optional, `game_limits.do_builder_base`). It sails over, collects the Elixir Cart, keeps the Builder Base builders and the Star Lab busy, and wins battles for the daily star bonus.
- **Learns.** It keeps a persistent memory, logs every attack and upgrade, tunes its own knobs (loot thresholds, attacks per run) from its stats, runs one experiment at a time, and rewrites `strategy.md` in a daily review.

## See it play

These are real screenshots Claude took through iPhone Mirroring during its first run. The captions are its own words from the session log. Other players' names, and mine, are blurred.

<p align="center"><img src="docs/images/timeline.jpg" alt="Six real screenshots from one run: home village, upgrade, scouting, two attacks, victory" width="100%"></p>

<table>
  <tr>
    <td width="50%"><img src="docs/images/game/home.jpg" alt="Home village"><br><sub><b>Reads the base.</b> Resources, builders (1/5 free), loot to collect.</sub></td>
    <td width="50%"><img src="docs/images/game/upgrade.jpg" alt="Upgrade confirm dialog"><br><sub><b>Starts upgrades.</b> It checks the confirm button costs elixir, not gems, and skips the Hammer of Building.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/images/game/scout.jpg" alt="Scouting an opponent base"><br><sub><b>Scouts.</b> Zooms on the available loot and hits Next until a base meets its loot threshold.</sub></td>
    <td><img src="docs/images/game/dragons.jpg" alt="Electro Dragons attacking"><br><sub><b>Attacks.</b> Lightning on the air defenses, then Electro Dragons in a line from one side.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/images/game/victory.jpg" alt="Victory screen, 67%, 357K gold"><br><sub><b>Banks the loot.</b> 1★ 67%, +391K gold +345K elixir with the league bonus. Then it logs the result for <code>coc stats</code>.</sub></td>
    <td><img src="docs/images/game/builders.jpg" alt="Builder list with timers" width="62%"><br><sub><b>Plans around timers.</b> It turns every builder timer into a clock time and picks its next wake-up from them.</sub></td>
  </tr>
</table>

### What it wrote afterwards

<p align="center"><img src="docs/images/run.png" alt="The agent's first real run: 2 attacks, a builder upgrade started, next wake-up chosen" width="90%"></p>

<p align="center"><img src="docs/images/strategy.png" alt="Excerpt of strategy.md, rewritten by the agent after 3 days" width="90%"></p>

## How it works

<p align="center"><img src="docs/images/how.png" alt="scheduler.py → run_session.exp → Claude Code agent → iPhone Mirroring, with persistent memory" width="90%"></p>

Two layers with a strict split:

1. **`scheduler.py`**: a small, reliable daemon. It decides only *whether a run may start now*: Mac idle, lid open, screen unlocked, on home Wi-Fi, iPhone nearby over Bluetooth, battery OK, no other Claude session holding computer use.
2. **The Claude agent** decides everything about the game, including when it should run next.

Computer use only works in an **interactive** Claude Code session (not `claude -p`), so `run_session.exp` drives the real TUI in a pseudo-terminal with `expect`. It answers the app-access prompt, nudges or kills stalled runs, and closes the session when the agent calls `coc finish`.

The full design doc, with the timing logic, safety rails and every config knob, is in [`docs/overview.html`](docs/overview.html) (or run `cocctl overview`).

## Requirements

- A Mac with **macOS 15 (Sequoia) or later** and **iPhone Mirroring** set up with your iPhone (iOS 18+)
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code)** with **computer use** available on your plan
- `python3` and `expect` (both ship with macOS). No pip packages.
- Clash of Clans installed on the iPhone and logged in

## Quick start

```bash
git clone https://github.com/arhxam/coc-agent.git
cd coc-agent
./bin/cocctl install          # installs to ~/.coc-agent and links `cocctl` into ~/.local/bin
```

Make sure `~/.local/bin` is on your `PATH`, then:

```bash
cocctl doctor                 # check prerequisites, permissions and the computer-use lock
cocctl run-now --attach       # first supervised run: watch it play (hands off the mouse)
cocctl start                  # run the background scheduler      (cocctl stop to stop)
cocctl autostart on           # optional: start at login via launchd
```

**One-time setup notes**

- Run `install` while you're on your **home Wi-Fi**. It records your router as "home" and finds your iPhone over Bluetooth. Add another network later with `cocctl home-here`.
- macOS will ask for **Screen Recording** and **Accessibility** for the app that launches Claude (your terminal, or `python3` with autostart). Grant both.
- Close any other Claude Code session that used computer use first. Only one session can hold it at a time, and `doctor` tells you who has it.
- Lock your iPhone and leave it near the Mac. The agent backs off if you're using the phone.
- **Adjust the seed memory to your base.** `app/memory_seed/` ships with my Town Hall 13 Electro Dragon setup as an example. The agent verifies and rewrites it on the first runs, but editing `attack_playbook.md` and `upgrade_priorities.md` to match your army gets you there faster. Then run `./bin/cocctl install --reseed-memory`.

## Everyday commands

| command | what it shows / does |
|---|---|
| `cocctl status` | next run and why, builder timers, recent runs |
| `cocctl logs -f` | live scheduler log |
| `cocctl transcript` | what the agent saw and did in the last run |
| `cocctl strategy` | the agent's current living strategy |
| `cocctl stats` | loot per attack, walls per day, "builder waited for loot" count |
| `cocctl availability` | which hours of the day runs actually work |
| `cocctl presence` | home network, iPhone nearby, idle, night |
| `cocctl pause` / `resume` | stop starting new runs without stopping the daemon |
| `cocctl next "+20m"` | override the next run time |
| `cocctl uninstall` | stop the scheduler and remove autostart (keeps `~/.coc-agent`; delete it for a clean slate) |

Config lives in `~/.coc-agent/config.json`. Set `game_limits.do_builder_base` to `true` to have the agent play the Builder Base as well. The useful knobs are the night window (`night_hours`), `max_run_minutes`, `model` (a cheaper model uses less of your plan), and `game_limits` (hard caps the agent can't tune past).

## Safety rails

**Enforced by code**
- A `PreToolUse` hook allows computer use for **iPhone Mirroring only**. Every other Mac app is blocked.
- The agent runs with `--permission-mode dontAsk` and an allow-list: read anything, edit only `memory/**`, run only `./bin/coc`. No web access.
- Hard time cap per run, stall detection, one run at a time, a daily run cap.

**Enforced by instructions** ([`app/CLAUDE.md`](app/CLAUDE.md))
- No real money, ever. No gems unless you turn on `game_limits.use_gems`.
- It never touches settings, your account, your clan or chat, and never removes or sells anything.

## Repo layout

| path | role |
|---|---|
| `bin/cocctl` | control CLI |
| `app/scheduler.py` | daemon: preflight checks, presence sensing, launches runs, applies the agent's next wake-up |
| `app/run_session.exp` | drives one interactive Claude Code session |
| `app/CLAUDE.md` | the agent's run protocol and hard rules |
| `app/tools/coc.py` | the `coc` helper the agent uses for time math, logging, stats, tuning and `finish` |
| `app/hooks/guard_apps.py` | hook that restricts computer use to iPhone Mirroring |
| `app/memory_seed/` | starting memory: `strategy.md`, playbook, priorities, walls, Builder Base notes, UI quirks |
| `examples/learned_memory/` | a snapshot of the memory the agent wrote itself after a day of runs |
| `app/config.default.json` | defaults (override in `~/.coc-agent/config.json`) |
| `docs/` | design overview and images (image sources in `docs/images/src/`) |

## Limits and risks

- ⚠️ **Automating Clash of Clans is against Supercell's Terms of Service.** Your account can be banned, no matter how human the taps look. Use it on an account you're willing to lose. This is an experiment in agentic computer use, not a cheat tool. See the [disclaimer](#disclaimer).
- It's slow and uses a lot of tokens: each run is many screenshots. On a Claude subscription that's plan usage. Lower it with fewer attacks per run, a cheaper `model`, or a longer `min_interval_minutes`.
- It only runs when the Mac is awake and unlocked, the lid is open, and the phone is reachable. In practice access, not loot, turned out to be the bottleneck (the agent worked this out itself, see the strategy screenshot above).
- Claude Code updates can change the wording of the computer-use access prompt. `run_session.exp` matches both known wordings. If runs start hanging at the prompt, check `logs/sessions/*.tty.log`.
- Screen coordinates and game UI change between versions. The agent records quirks in `ui_map.md` and adapts, but expect occasional `needs_human` runs.

## Disclaimer

**Educational and research use only.** This project shows how an AI agent can operate a real app through macOS computer use: reading the screen, planning, acting and learning from results. It is published so people can study and learn from that. It is not meant to give anyone an advantage in the game, and it is not a commercial product.

**Not affiliated.** coc-agent is an independent, unofficial project. It is not affiliated with, endorsed by, sponsored by or approved by Supercell Oy. Clash of Clans and its names, logos, art and characters are trademarks and copyrighted material of Supercell Oy. They are used here only to identify the game and describe what the project does. This material is unofficial and is not endorsed by Supercell. For more information see Supercell's Fan Content Policy: [www.supercell.com/fan-content-policy](https://www.supercell.com/fan-content-policy). The game screenshots are from my own account's gameplay, with other players' names blurred. Claude and Claude Code are trademarks of Anthropic, and iPhone, iPhone Mirroring and macOS are trademarks of Apple Inc. coc-agent is not affiliated with or endorsed by Anthropic or Apple.

**Against the game's rules.** Supercell's [Terms of Service](https://supercell.com/en/terms-of-service/) prohibit bots, automation and unauthorized third-party software. Using this project with a Clash of Clans account violates those terms and can get the account suspended or permanently banned. If you run it, you accept that risk and are responsible for complying with every agreement that applies to you, including Supercell's, Apple's and Anthropic's terms.

**What it doesn't do.** It doesn't modify, decompile or inject code into the game, read its memory, intercept its network traffic or get around any anti-cheat or security measure. It only sees and taps the screen through iPhone Mirroring, the way a person would. Please don't fork it to add any of those things or to dodge detection, and don't sell it, rent it out or offer it as a service.

**No warranty.** The software is provided "as is", without warranty of any kind, as stated in the [MIT License](LICENSE). The authors aren't liable for banned or lost accounts, lost progress or in-game items, spent resources, usage costs on your Claude plan, or any other damage from using it.

**Rights holders.** If you represent Supercell or another rights holder and want something changed or removed, please [open an issue](https://github.com/arhxam/coc-agent/issues) and I'll respond promptly.

## License

[MIT](LICENSE)
