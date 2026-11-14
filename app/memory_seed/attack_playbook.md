# Attack playbook

## Current army (seen 2026-11-12)
9 Electro Dragons, 5 Wall Breakers, 11 Lightning Spells, siege machine, Barbarian King, Archer Queen, Grand Warden.
Quick Train → train the same army after each attack.

## Target selection (farming)
- Goal = **loot to keep storages at target**, not trophies. A 1-star with ≥50% while hitting the storages and collectors is fine.
- Scout timer is ~30 s. Zoom on "Available loot" at the top-left immediately.
- Attack if gold+elixir ≥ the `min_loot_gold_plus_elixir` knob (`coc config`; start 1M; tune it from `coc stats`). "Dead bases" (full collectors/mines, inactive-looking) are best.
- Skip: bases with nearly empty loot, maxed-looking TH14+ with 4+ visible infernos/scatters when your army is a TH13 one.
- Need dark elixir → prefer bases with high DE and exposed drills/DE storage.
- Max `next_per_attack` Nexts (each Next costs a little gold).
- Ranked attacks are limited per day (8). After that, use the regular multiplayer battle (≈1,200 gold to search).

## Deployment: Electro Dragon "zap-dragon" (default)
1. Zoom and **find the air defenses** (tall dark launchers, usually 4). If 2 are close together on one side, Lightning them: about 3 lightning per AD at this level. Don't scatter lightning on unknown buildings.
2. Wall Breakers are optional for E-drag; use them on a wall segment near the heroes' path.
3. Drop all Electro Dragons in a **line along one side** (the side with the most outer buildings/collectors, away from the Inferno/Scattershot cluster if visible), spaced so their chains overlap.
4. Siege machine (if a Lava Blaster/Balloon type) + Grand Warden behind the dragons; King and Queen on the same side about 5 s later.
5. Warden ability when the dragons start taking heavy damage in the core. King/Queen abilities when their health drops to about half.
6. Leftover lightning: finish off air defenses or the Eagle Artillery when it's low.

## Learnings
- 2026-11-12: 1★ 72% vs TH13. Dragons cleared the left side but died before the TH. Lightning went on far-side defenses without confirming they were ADs (wasted). → Identify ADs first; zap ADs on the dragon path.
- 2026-11-12: Storages were near full, so most of 1.79M gold / 1.73M elixir was wasted. → Banking is right, but attack when there's room: farm right after spending on an upgrade, or target the resource that has room.
