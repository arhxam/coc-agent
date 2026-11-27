# Strategy (living document, owned by the agent)

_Last revised: (seed). On the first run, rewrite this from the active profile (`./bin/coc direction`) and what
you see in game. Keep it to one screen. Log changes in the changelog at the bottom._

## Profile
- Active profile: (fill in from `./bin/coc direction`). If the owner changes profile, re-derive this file.

## North-star metrics
1. **Builders and lab never idle for lack of loot** (`coc stats` → "idle builder had to wait for loot" → 0).
2. The profile's own goal (storages at target / Town Hall progress / walls per day / trophies).
3. Few wasted runs (phone_in_use / deferred during hours we already know are bad).

## Economy
- Storage target: `storage_target_fill` (see `coc config`). Spend from the bank when a builder or the lab frees up.
- Don't attack for a resource that's already full (wasted loot).

## Builder queue approach
- Follow `upgrade_priorities.md` (written from `app/knowledge/upgrade_order.md` for this Town Hall).
- Long jobs before long gaps (night); stagger finish times.

## Walls
- Pace: `walls_per_day_target` / `walls_per_run`, surplus above the reserve only.
- Unknowns to verify (record in walls.md): does a wall upgrade need an idle builder? Row/multi-select? Gold and elixir both accepted?

## Attacks
- Recipe: (pick from `app/knowledge/attacks.md` for the account's army; record it in attack_playbook.md).
- Thresholds: `min_loot_*` knobs; tune from `coc stats`.

## Timing pattern (update after looking at `coc availability`)
- Night window: main work time. Day: only when the owner is idle; use `--opportunistic-after`.

## Open experiment
- none yet. First, gather a baseline: 2 days of stats with the defaults.

## Changelog
- (seed) generic starting point; the first run fills in the account specifics.
