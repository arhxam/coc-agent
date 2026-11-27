# Profile: endgame (maxed or nearly maxed)

**Goal:** finish the last 10%: walls, hero equipment, research, and anything left. At max Town Hall that's
all there is, so farm a lot and pour the surplus into walls.

## Priorities
1. Any remaining building, hero or lab upgrade first. Builders and lab never idle while something is left.
2. **Walls are the main sink:** farm and upgrade walls every run (`walls_per_day_target` is high). Use both gold
   and elixir for walls when the game allows it, and alternate so neither storage caps out.
3. **Hero equipment (Blacksmith):** keep ore flowing into the equipment the main army uses most
   (if `use_hero_equipment_ore`). Ore comes from the Trader, star bonus and events, not from storages.
4. Keep the Builder Base and other side modes (if enabled) busy; they're cheap progress.

## Economy
- Storages don't need to be full: there are few big builder jobs left. Keep `storage_target_fill` around 80%
  so attack loot isn't wasted, and spend everything above it on walls.
- More attacks per run is fine; loot per attack is the metric. Prefer bases with lots of loot over trophies.
- If this isn't actually max Town Hall and `allow_town_hall_upgrade` is on, upgrade the Town Hall when everything
  but walls is done, and tell the owner in the summary that `max-out` is the better profile after the upgrade.
