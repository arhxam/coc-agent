# Profile: fast-progress (climb Town Halls quickly)

**Goal:** reach a high Town Hall with a strong army as fast as possible. Defense matters little: losing some
loot to raids is acceptable. Builder time still must never be wasted.

## Priorities
1. **Every builder busy, always.** If the ideal job is unaffordable, start a cheaper short one instead of waiting.
2. **Offense and economy first:** Laboratory, Army Camps, Barracks/Spell Factory unlocks, Clan Castle, the
   farming army's troops and spells (lab never idle), storages (bigger bank), then heroes.
3. **Town Hall early:** upgrade the Town Hall (if `allow_town_hall_upgrade`) as soon as the lab, army camps,
   Clan Castle and the main farming troops are done at this level. Leave defenses for builders that would otherwise sit idle.
4. After a Town Hall upgrade, build the new buildings first (cheap, fast, and they raise storage and army capacity).
5. Defenses: only the ones that matter most for loot protection (air defense, splash defenses), and only to fill idle builders.
6. Walls: a token amount (`walls_per_day_target`, low by default) only when storages overflow.

## Economy
- Spend, don't bank: keep storages around `storage_target_fill` (75% by default) and put loot to work immediately.
- Farm with the cheapest, fastest army that gets the loot (see `app/knowledge/farming.md`), so the army is ready again quickly.
- Hero upgrades are fine even if it weakens attacks for a while, as long as farming still works without them.
