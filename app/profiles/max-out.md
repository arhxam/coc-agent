# Profile: max-out (bank, don't drain)

**Goal:** max out every Town Hall level as fast as possible, then move up. Builder time is the scarcest
resource in the game, so the #1 metric is **"no builder or lab ever waits for loot."**

## 1. Bank, don't drain: keep storages full
Keep gold, elixir and dark elixir at or near full (`storage_target_fill`, default 90%) *all the time*. Then the
moment a builder or the lab frees up, the next upgrade starts immediately.
- Farm whenever a storage is below target and the army is ready. Night is the best time to do it.
- Spend from the bank on builder and lab upgrades whenever one is free. Then farm the bank back up.
- A full storage means attack loot for that resource is wasted. When storages are full, prefer walls or a
  target rich in the resource you lack.

## 2. Walls are a separate track
Walls are the overflow valve and a slow daily grind, not part of the builder queue.
- Upgrade a few segments every day (`walls_per_day_target`, a little each run: `walls_per_run`), but only with
  the **surplus above the reserve**.
- **Reserve** = enough to start every builder or lab job you expect in the next `wall_reserve_hours`.
- When a storage is at or near full and loot would otherwise be wasted, put more into walls (within `max_walls_per_run`).

## 3. Time it around the owner's life
The night window is prime time for long farming sessions. During the day, runs happen only when the owner is
away from the Mac and not using the phone.
- Start **long upgrades in the evening or at night's start** so they finish when a run can act.
- Before the night window ends, leave every builder and the lab busy on the longest sensible jobs, and the storages full.

## Upgrade order and Town Hall
- Offense first (lab, army camps, Clan Castle, the farming army's troops and spells, heroes), then the key
  defenses, then storages and resource buildings, then the rest. See `app/knowledge/upgrade_order.md`.
- **Town Hall:** upgrade it (if `allow_town_hall_upgrade`) once offense is maxed and the important defenses are
  done or in progress, i.e. when only walls, traps and minor buildings are left. Don't sit at a maxed Town Hall.
- Right after a Town Hall upgrade: build every newly unlocked building first (if `allow_new_buildings`), they are cheap and fast at level 1.
