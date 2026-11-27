# Core principles (any Town Hall, any profile)

## Time is the real currency
- **Builder time is the scarcest resource.** An idle builder is progress lost forever. A slightly worse
  upgrade started now beats the perfect one started in 3 hours.
- **Lab time is second.** Research is long and gates the army that farms everything else. Keep it busy.
- Other parallel queues follow the same rule when the account has them: hero upgrades (they use a builder),
  pet house, Blacksmith, helpers, Builder Base builders and Star Lab.
- **Match job length to when you can act.** Long jobs at night or before a long gap; short jobs when a run is
  coming soon anyway. Stagger finish times so builders don't all free up during hours when runs fail.

## Loot and storages
- Loot comes from attacks (storages, collectors/mines, Town Hall and Clan Castle of the defender), collectors
  at home, the Elixir Cart / Builder Base, rewards and events.
- **A full storage wastes loot.** Attack when there's room, or target the resource that has room.
- Storages being full when a builder frees = the job starts instantly. Storages empty = the builder waits.
  The right fill level depends on the profile (`storage_target_fill`).
- Attacking much lower Town Halls usually gives a loot penalty; attacking the same or higher TH gives full loot.
- Wins pay a league bonus on top of stolen loot. Higher league = bigger bonus.
- Collect collectors/mines regularly; they cap out, and full collectors on your base are free loot for raiders.

## Offense before defense (for progress)
- A stronger farming army makes every future upgrade cheaper in real time. Lab, army camps, Clan Castle,
  spells and the farming troops come first in most profiles.
- Defense matters for war, trophies and losing less loot, and profiles weigh that differently.

## Heroes
- Heroes use a builder (or a hero hall slot) while upgrading and can't attack. Don't put all heroes down at
  once unless the farming army works without them. Profiles may cap this (`max_heroes_upgrading`).

## Walls
- Walls are a near-infinite sink. Treat them as the overflow valve: spend only the surplus above what the
  next builder/lab jobs need. At higher levels walls can often be paid with gold *or* elixir: alternate.
- Verify in game whether wall upgrades need a free builder and whether several walls can be selected at once.

## Spending rules
- Never spend real money. Gems only if the owner set `use_gems`.
- Magic items (books, hammers, potions, wall rings, runes) only if the owner set `use_magic_items`. Then: books
  and hammers on the **longest** jobs, builder/research potions when every builder/the lab is busy on long jobs,
  wall rings on the most expensive walls, runes only when a full storage unblocks an idle builder.

## Learn from evidence
- One change at a time, measured (`coc experiment`). Log everything; the logs are how future runs get smarter.
