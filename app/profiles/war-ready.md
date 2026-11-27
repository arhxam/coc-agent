# Profile: war-ready (strong base for clan war)

**Goal:** a base that defends well in clan war and CWL, and an army that is ready when the clan needs it.
Progress steadily, but don't leave holes in the base.

## Priorities
1. **Every builder busy**, as always.
2. **Defense and Clan Castle get real priority:** Clan Castle, then the key defenses for this Town Hall
   (Eagle Artillery / Scattershot / Inferno / X-Bow / Air Defense / splash), then the rest of the defenses, then traps.
3. **Heroes: never more than `max_heroes_upgrading` (default 1) upgrading at once.** Heroes matter for war attacks
   and they defend in war. Stagger hero upgrades so the others stay available.
4. Offense research stays continuous (lab never idle), focused on the clan's war army.
5. **Walls are a first-class track:** `walls_per_day_target` is higher than in other profiles. Walls are a big part of
   war defense; upgrade the core ring first, then outward.
6. **Town Hall** (if `allow_town_hall_upgrade`) only after the defenses and walls are mostly done at this level. Don't rush.

## Notes
- The agent never takes part in war attacks or changes the war base layout itself (those need a human).
  It keeps the base and army ready.
- If `donate_to_clan` is on, fill donation requests with troops you already have spare (war clans rely on it).
