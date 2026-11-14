# Strategy (living document, owned by the agent)

_Last revised: 2026-11-13 (seed). Rewrite freely; keep it to one screen. Log changes in the changelog at the bottom._

## North-star metrics
1. **Builders and lab never idle for lack of loot** (`coc stats` → "idle builder had to wait for loot" → 0).
2. Storages ≥ target fill when a builder frees up.
3. Walls: steady daily progress from surplus only.
4. Few wasted runs (phone_in_use / deferred during hours we already know are bad).

## Economy: bank, don't drain
- Keep gold, elixir and DE at or near `storage_target_fill` (start: 90%).
- A builder or the lab frees up → start the next job immediately from the bank → farm the bank back up.
- Don't attack for a resource that's already full (wasted loot). If everything is full, it's wall time.
- Reserve for walls = cost of the jobs expected to start within `wall_reserve_hours` (start: 12 h).

## Builder queue approach
- Follow `upgrade_priorities.md`. Prefer jobs whose finish time lands in a window when runs work (night, or historically idle hours).
- Evening / start of night: put free builders on the **longest** valuable jobs.
- Stagger finish times so builders don't all free up in the same busy daytime hour.

## Walls (separate track)
- Target `walls_per_day_target` (start: 6) segments/day, about `walls_per_run` (start: 3) per run, surplus only.
- Overflow rule: if a storage is ≥ 98% and the next builder job is covered, dump the excess into walls (≤ hard limit).
- Unknowns to verify on the first runs → write the answers into walls.md: does a wall upgrade need an idle builder? Is multi-select / row upgrade available? Cost per level at TH13?

## Attacks
- Default: zap-dragon (see attack_playbook.md). Take bases with gold+elixir ≥ `min_loot_gold_plus_elixir` (start: 1M), or high DE when DE is the gap.
- Night window: farm repeatedly until storages are at target (army-ready → attack → retrain).

## Timing pattern (update after looking at `coc availability`)
- Night window (00:30–08:30): main work time. Expect runs every army cycle while storages are below target.
- Day: only when the owner is idle; use `--opportunistic-after` instead of guessing exact times.

## Open experiment
- none yet. First, gather a baseline: 2 days of stats with the defaults.

## Changelog
- 2026-11-13 seed: bank-first economy, walls as a separate surplus track, night-first timing (owner's direction).
