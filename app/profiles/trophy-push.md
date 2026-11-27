# Profile: trophy-push (climb leagues)

**Goal:** a higher league. Attack for stars and trophies, not loot. Higher leagues also pay a bigger league
bonus, so loot follows. Builders still never sit idle.

## Attacks
- The knob `attack_goal` is `trophies`. Scout for bases the army can **3-star or 2-star reliably**: the same or lower
  Town Hall, weak air (for air armies) or weak ground (for ground armies), compact enough for a one-side attack.
- Don't take bad matchups for loot. Skip bases above your strength (Next, up to `next_per_attack`).
- Use the strongest army the account has, with heroes. Log stars, destruction and trophies on every attack
  (`"trophies": +N` in the attack log) so `coc stats` can compare armies.
- If ranked attacks are limited per day, use them all; they're the point of this profile.

## Upgrades
1. **Heroes up:** never more than `max_heroes_upgrading` (default 1) upgrading at once.
2. Offense first: lab never idle on the main army's troops and spells, army camps, Clan Castle, siege machines.
3. Then defenses (a stronger base loses fewer trophies on defense), then walls.
4. Town Hall (if `allow_town_hall_upgrade`) when offense is maxed. A higher TH meets stronger opponents, so don't rush it.
