# Attack recipe library

Each recipe has a short name: put it in the attack log (`"strategy": "<name>-v1"`) so `coc stats` can compare.
`memory/attack_playbook.md` holds the account's current army and the recipe it uses; improve it from results.
If `strategy.attack_style` in `coc config` names a recipe, use that one; `auto` = your choice.

**General deployment rules** (all recipes)
1. Zoom first. Find the defenses that counter the army (air defenses for air armies; splash defenses for swarms).
2. Spells on what matters: Lightning/Earthquake on air defenses on the army's path; Rage/Freeze/Heal where the
   army will fight. Don't spend spells on unknown buildings.
3. Deploy from **one side**, as a line or tight groups, toward the core. Funnel: take the outer buildings on both
   edges first so the main army walks inward instead of around the base.
4. Heroes and Clan Castle troops follow the main army; use abilities at about half health.
5. End the battle (End Battle → confirm) once the loot is taken and nothing more is happening, to save time.

## barch (TH3–7, loot raid)
Barbarians + Archers. Deploy small groups at full collectors and exposed storages around the edge. No funnel needed.

## giant-healer (TH6–9)
Giants tank, Wizards/Archers behind, 1–2 Healers behind the giants once air defenses are out of reach. Wall Breakers to open a wall.

## mass-dragon (TH7–10)
Dragons (+ Lightning on 1–2 air defenses, Rage). Deploy all dragons in a line along one side, spaced out.
Fails against many air defenses in the core: pick bases with exposed air defenses.

## loonion (TH8–11, balloons + minions)
Balloons in groups targeting defenses, minions behind to clean up. Lightning/Haste. Weak against Air Sweepers.

## sneaky-goblin (TH11+, super troop loot raid)
Boost Sneaky Goblins (dark elixir). Groups of goblins at storages/collectors from 2–3 points; they go invisible
briefly and hit resources hard. Doesn't aim for stars; aims for loot. Great for gold/elixir.

## super-barb (TH11+, super troop farm)
Boost Super Barbarians. Spread them along one side with a Rage; they rage after kills and clean the edge fast. 1-star farming.

## edrag-zap (TH11–15)
Electro Dragons + Lightning on air defenses on their path (~3 per AD, check the AD level) + siege + heroes.
Line them along the side with the most outer buildings, away from the Inferno/Scattershot cluster.
Warden ability when the dragons take heavy damage in the core.

## dragon-rider (TH13+)
Dragon Riders target defenses and are tanky. Line them along one side with Rage/Freeze; Lightning on air defenses near the entry.

## Writing your own
Copy the shape: name, when to use, army, deploy steps, failure modes. Log at least 5 attacks before judging it.
