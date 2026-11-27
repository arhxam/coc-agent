# Farming (getting loot efficiently)

## The loop
army ready → scout → take a base that pays → deploy → re-train (or Quick Train) → log → repeat.
In many game versions the army is ready again right after a battle, so **attacks per run is the farming limit**.

## Choosing a target (≈30 s of scouting)
- Zoom on **Available loot** first. Take it if it meets your `min_loot_*` knobs and has the resource you need.
- **Dead bases** pay best: full collectors/mines (visible full bars or icons), inactive look, low Town Hall level
  for its walls/defenses. Loot sitting in collectors is easy to take from the edge.
- Avoid much lower Town Halls (loot penalty) and bases clearly stronger than your army.
- Need dark elixir? Prefer exposed drills and a reachable DE storage.
- Each Next costs a little gold. Cap them with `next_per_attack`; lower thresholds if you hit the cap often.

## Farming armies by Town Hall (simple, one-side deployments suit a vision agent best)
- **TH3–6:** Barbarians + Archers ("barch"), Giants + Archers/Wizards. Collector raids from the edges.
- **TH7–9:** Giants + Healers + Wizards; mass Dragons (TH7+ with Lightning for air defenses); BAM (barbarians, archers, minions) for collector raids.
- **TH10–12:** mass Dragons / Balloons with Lightning; Super Barbarians or Sneaky Goblins (super troops, boosted
  with dark elixir) are fast, cheap loot raids that don't need 3 stars.
- **TH11+:** Electro Dragons spammed along one side with Lightning on air defenses; Dragon Riders at higher THs.
- Prefer armies that train fast or are ready instantly; loot per *run* matters more than stars.

## What "good" looks like
- Track avg loot per attack by strategy name (`coc stats`). Raise `min_loot_*` while avg nexts stays low.
- 1 star with the storages and collectors hit is a fine farming result. Trophy-push profiles differ.
- Loot wasted (storage full) is a planning mistake, not bad luck: farm right after spending.
