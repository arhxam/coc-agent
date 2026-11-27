# Roadmap: making coc-agent useful for everyone

coc-agent started as one person's agent for one account (TH13, Electro Dragons, "bank loot, walls from surplus").
This document lists what makes it general, what has shipped, and the concrete next steps. Each item says
*what* changes, *why* it adds value, and *where* in the code it goes.

## Principles
1. **The owner chooses the goal; the agent chooses the moves.** Profiles, switches and notes are the owner's
   levers. Everything else is the agent's to learn and tune from evidence.
2. **Nothing account-specific in the shipped code.** The first run discovers the account. Game know-how lives
   in `app/knowledge/`, account facts live in `memory/`.
3. **Measure progress, not activity.** Builder/lab utilisation, upgrades per day, loot per attack, Town Hall and
   trophies over time. The agent should be able to tell whether it is actually getting better.
4. **Safe by default.** Every new capability that spends something or touches other players is a switch that is off by default.

## Shipped (v2: profiles and generalisation)

| # | improvement | value | where |
|---|---|---|---|
| 1 | **Strategy profiles**: `max-out`, `fast-progress`, `war-ready`, `trophy-push`, `endgame`, `frugal` | players pick the goal that fits them instead of inheriting one person's | `app/profiles/`, `coc direction` |
| 2 | **Layered config**: defaults ← profile ← owner; only the owner's changes live in `config.json` | profiles apply cleanly; upgrades don't clobber settings | `app/cocconf.py` |
| 3 | **Owner notes** (`cocctl note "..."`) and **attack style** (`strategy.attack_style`) | plain-language direction without editing prompts | `strategy.notes`, `coc direction` |
| 4 | **Setup wizard**, `cocctl profile`, `cocctl config get/set/unset` | no JSON editing needed; typos caught by `doctor` | `app/tools/cocsetup.py`, `bin/cocctl` |
| 5 | **Onboarding survey** on the first run | works on any Town Hall and army out of the box | `app/CLAUDE.md`, `scheduler.first_run()` |
| 6 | **Knowledge base**: principles, upgrade order by TH, farming, attack recipe library, Builder Base, side modes, UI basics | the agent starts from good general play, not from zero or from one account | `app/knowledge/` |
| 7 | **Generic seed memory** | no wrong assumptions about the account | `app/memory_seed/` |
| 8 | **New switches**: `allow_town_hall_upgrade`, `allow_new_buildings`, `use_magic_items`, `use_hero_equipment_ore`, `do_clan_capital`, `max_attacks_per_day` | the agent can progress through Town Halls; owners control every spend | `config.default.json`, CLAUDE.md hard rules |
| 9 | **`coc progress`**: per-day builder/lab utilisation, blocked-by-loot, fill, upgrades, research, walls, attacks, loot, trophies, Town Hall | "is it getting better?" is answerable | `app/tools/coc.py` |
| 10 | **Weekly review**: week-over-week progress, Town Hall decision, memory pruning | long-horizon improvement, not just daily tweaks | scheduler prompt, CLAUDE.md |
| 11 | **Measured experiments** (`coc experiment start/status/end`), one at a time, compared with the attacks before | real A/B evidence instead of vibes | `app/tools/coc.py` |
| 12 | **Profile-scoped tuning**: knobs tuned under one profile don't leak into another | switching profiles gives sane starting values | `coc.game_knobs()` |
| 13 | **Daily caps** (`coc today`, attack-cap warning) | predictable account activity | `app/tools/coc.py` |
| 14 | **Python 3.9 support**, tests, CI on macOS + Linux | works with the macOS system python; contributions are safe to merge | `tests/`, `.github/workflows/ci.yml` |

## Next (concrete, in priority order)

1. **Notifications beyond macOS banners.** Optional `notify.ntfy_topic` / `notify.telegram` / `notify.webhook`
   so owners see `needs_human` and daily summaries on the phone. *Where:* `scheduler.notify()`. Off by default;
   the payload is only the run summary.
2. **Daily digest.** One message a day: upgrades started, walls, loot, builder utilisation, next Town Hall ETA.
   *Where:* a `coc digest` command plus a scheduler hook after the daily review.
3. **Token and cost tracking per run.** Parse the session transcript for usage, log `tokens_in/out` per run and show
   `cost per upgrade started` in `coc stats`. Lets `frugal` tune itself against a budget (`budget.max_tokens_per_day`).
4. **Structured base model.** Replace free-text queue items with `memory/buildings.json` (building, level, max for TH)
   filled during onboarding, so `coc progress` can show "% maxed for this Town Hall" and the TH decision is computed, not guessed.
5. **Coordinate cache with self-healing.** Store verified tap targets per screen in `memory/ui_map.json`; try the cached
   point first, fall back to vision if the screenshot doesn't match. Fewer screenshots per run = cheaper and faster.
6. **Recipe scoring.** `coc stats --by-recipe` across Town Hall brackets, plus a shared, anonymised
   `knowledge/recipes_results.md` contributors can update from their own logs.
7. **More profiles from the community.** e.g. `builder-base-focus`, `clan-games-grinder`, `hero-rush`, `cwl-week`
   (a temporary overlay with an end date: `strategy.profile_until`).
8. **Scheduled profile switches.** `strategy.schedule: [{"from":"Fri 08:00","to":"Mon 08:00","profile":"..."}]` for
   raid weekends or CWL weeks.
9. **Multiple accounts.** `COC_HOME` per account plus a `cocctl --account <name>` flag; the scheduler runs one at a time
   and switches accounts through the in-game Supercell ID switcher only if the owner explicitly enables it.
10. **Android support.** A second "screen bridge" (scrcpy window) behind the same guard hook, so non-iPhone players can use it.
11. **Dry-run / replay harness.** Feed recorded screenshots to the agent to test CLAUDE.md changes without touching a real account.

## Out of scope (on purpose)
- Anything that reads game memory, intercepts traffic, injects code or evades detection.
- Clan war attacks and chat. Those affect other people and need a human.
- Spending real money, and spending gems or magic items without the owner's switch.
