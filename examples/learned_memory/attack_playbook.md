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
- 2026-11-13: **3 Lightning L9 kill a TH13 air defense** (ADs = yellow/black rocket clusters). Zap 3 ADs with 11 zaps *before* deploying. No heroes: 30% (strong TH13, only 2 ADs zapped with 4 each) vs 67% 1★ (3 ADs zapped). Loot 1.14M and 0.74M.
- 2026-11-13: No training time; attack back to back. Deploy leftover Wall Breakers to end the battle once the dragons are dead.
- 2026-11-12: 1★ 72% vs TH13. Dragons cleared the left side but died before the TH. Lightning went on far-side defenses without confirming they were ADs (wasted). → Identify ADs first; zap ADs on the dragon path.
- 2026-11-12: Storages were near full, so most of 1.79M gold / 1.73M elixir was wasted. → Banking is right, but attack when there's room: farm right after spending on an upgrade, or target the resource that has room.

## 2026-11-27: current recipe "edrag-line-left" (TH12-13 opponents; 5 attacks, avg 1.92M, stars 3/2/2/3/3)
- Army: 9 E-drags, 3 balloons, 70 event barbarians (1 per click, not needed), siege, King + Minion Prince + Warden + Royal Champion, 11 Lightning.
- Take: gold+elixir >= 1.2M, or TH12-or-weaker with gold >= 450k. About 1 Next per attack.
- Batches: (1) pan drag + screenshot; (2) 9 E-drags on a line along the left grass, 3 balloons, siege and heroes in the middle, then screenshot + full zoom; (3) Lightning: 4 on the nearest air defense (yellow/black rockets), 7 on an inferno or second air defense; King, Prince, Champion abilities at once, Warden +8 s; wait 65-75 s.
- 100% in ~80-90 s on open or weak bases. On compact TH12s the army dies at ~80% with 1 min left: End Battle + Okay (nearly all loot is already taken by then).

## 2026-11-18: older recipe "edrag-clump-left"
- Army: 9 E-drags, 2 Minions, 1 Goblin, siege (balloon type), 9 Lightning + 2 of a second spell, King + Warden (others upgrading). Game shows "Army Boosted / Heroes Boosted".
- Opponents are TH14-16; Next costs 1,500 gold. Any win pays a 300k gold / 300k elixir / 2,050 DE bonus.
- Results: TH14 708k gold -> 3 stars, 1.01M gold banked; TH14 510k -> 2 stars 70%, 625k; TH15 843k -> 48% 0 stars, 442k; TH15 1.31M -> 38%, 596k.
- Rule: first TH14-or-weaker (brown/gold walls, few red/blue TH15-16 buildings) with gold >= 450k. Skip TH15+ unless gold >= 1.2M.
- Steps: drag-pan right, deploy everything on the left grass in one batch, 4 zaps each on the 2 air defenses nearest the dragon path (5th on one), second spell on the clump, hero abilities ~10 s later, wait ~90 s.
