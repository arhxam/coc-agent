# UI map and quirks (iPhone Mirroring + Clash of Clans)

Coordinates depend on where the iPhone Mirroring window is. Center it first (Window → Center) so these stay roughly stable.

## Mirroring window
- An invisible overlay from another app (a dictation tool) sat over the lower-middle of the screen and blocked clicks on the Attack button (2026-11-12). Fix: with iPhone Mirroring frontmost, menu bar **Window → Center** (click "Window" in the menu bar, then "Center").
- Dragging the window by its title bar was unreliable; use Window → Center instead.
- The game runs in landscape inside the mirroring window.

## Clash of Clans (home village, landscape)
- Battle / Attack button: bottom-left.
- Builder count + list: top-middle ("Builders x/y"); tap it to see upgrades in progress and suggestions.
- Resources: top-right (gold, elixir, dark elixir, gems). Zoom to read.
- Shop: bottom-right. **Avoid** except to place nothing. Never buy.
- Army / Quick Train: icon near Battle at bottom-left.
- In battle: troop bar along the bottom; "Next" button at the bottom-right while scouting; "Available loot" at the top-left; "End battle" at the bottom-left.
- After a battle: "Return Home" button in the bottom center.

## Seen 2026-11-13 (window NOT centered: game area = screen x 380-992, y 444-726; zoom that region to read)
- Open the game: Cmd+3 (Spotlight on the phone) → type "Clash of Clans" → click the Top Hit.
- Home: Battle (446,692). Builder icon "x/5" (914,658) opens the "Buildings & Heroes" list with timers and suggested upgrades; X at (942,455). Scrolling that list with the mouse wheel did not work.
- Battle menu: "Find a Match 1200 gold" (490,636) → army screen → green "Attack!" (875,689).
- In battle: Next (916,646). Troop bar: Wall Breaker (525,693), E-drag (555,693), siege (592,693), Lightning (625,693). End Battle/Surrender at about (449,655): keep clicks away.
- Deploy spots that worked at the left edge: around (387,644), (386,662), (394,666). Many other left-edge clicks hit the red zone; check the troop count after deploying and repeat.
- Result screen: Return Home (685,680).
- Upgrade dialog: green Confirm with the resource icon (782,681). The blue "Hammer of Building" button to its left and the Gold Pass banner above: never tap.
- "Free!" gem button on the right edge opens the shop: not touched yet.

## Window CENTERED (verified 2026-11-13 14:40): game area = x 380-992, y 335-615
- Same x as the list above, **y is 109 less**. Battle (446,580) → Find a Match (490,527) → Attack! (876,580). Next (916,537). Loot numbers: zoom (380,335)-(560,440).
- The window can start half off-screen at the left after connecting; always do Window → Center once the game is in landscape.
- "iPhone microphone is not available from Mac" dialog on game start: click OK.
- "iPhone in Use" card with a Connect button: one Connect click is fine (it only works if the phone is locked). If mirroring drops again mid-run, the owner picked up the phone: finish `phone_in_use`.

## Seen 2026-11-16 (window centered)
- First screenshot right after open_application can fail ("capture returned nil"); a second one works.
- Left side buttons: clan chat (441,468), **clan war (441,500): do not tap**. Pink domes = Elixir Storages.
- Selected-building bar sits at y≈553: Info (618,553). Info panel X at (870,355).
- Wall bar: Info, Select Row, Upgrade More, Upgrade gold (708,553), Upgrade elixir (752,553), Wall Ring (798,553: never). Confirm (782,571). Goblin offer X (850,403).
- Battle: Lightning (689,582), CC lightning (724,582), E-drag (553,584), siege (587,584), Warden (621,584), Royal Champion (653,584). Deploy on left grass around (432-440, 425-485) without panning: all 9 E-drags landed.
- Result screen can show "Claim Reward" (Treasure Hunt chest, free) at (686,571): tap chest ~4 times at (685,480), then Continue (689,589).
- Connect can sit on "Connecting to iPhone" for ~30 s before the home screen appears; wait up to ~40 s before judging.
- "Update is available!" dialog on the loading screen (Update button at about (685,610), window not centered): never tap, it leaves the game for the App Store → needs_human.
- Mirroring drop mid-game = window turns portrait with "iPhone in Use / Connect".

## Seen 2026-11-18 (new game version, window not centered, unverified small text)
- Home layout looks unchanged: Battle bottom-left, resources top-right, Build hammer bottom-right with "3/5" and "1/1" counters above it (about (914,660) and (936,660)), "Free!" shop button on the right edge (never).
- Window menu: Center is the 5th item (291,134). A screenshot taken while a menu is open may fail; that is the capture tool, not the click.

## Seen 2026-11-18 10:24 (window NOT centered after a reconnect: game area x 544-1156, y 444-724 = centered x +164, y +109)
- "Anyone there? / Reload game" (685,500 centered) can hang on Loading: Cmd+1, Cmd+3, type the name, click the Top Hit instead.
- Builder icon "3/5" at (1078,660) opens "Buildings & Heroes" on the right (x 955-1115): busy jobs on top, then Suggested upgrades (rows at y≈530, 565, 600), Other upgrades below; X at (1105,454). Bottom tabs: builders (972,705), lab (1013,705), forge (1054,705), pets (1095,705).
- "3/5" on the builder icon means 3 FREE of 5.

## Seen 2026-11-27 (window as opened, not centered by me: game area x 296-906, y 337-617; worked all run)
- Connect card (portrait): Connect (601,577), ~35 s to the phone. Cmd+1, Cmd+3, type the name, Top Hit (505,273), ~25 s to the village.
- Home: Battle (361,581); builder/Build icon (830,551) opens the list. List: X (857,348), rows x≈782, tabs builders (723,598), lab (765,598). Row y from a zoom of (600,337)-(906,617): y = 337 + zoom_y x 0.454.
- Upgrade dialog: green Confirm with resource icon (697,573); zoom (584,550)-(800,595) to check the icon. Blue Hammer button to its left: never. Dialog X (785,357). After a research Confirm the same spot is "Finish Now (gems)": close with X.
- Battle menu: Find a Match (398,528) -> army screen Attack! (792,581). Scout: Next (831,541); loot zoom (296,337)-(601,477).
- Battle: pan with drag (450,500)->(760,440); left grass runs about (445,400)->(555,510) (or (447,432)->(566,536) on small bases). Troop bar y=587: E-drag 435, balloons 466, x70 slot 498, siege 538, King 571, Minion Prince 603, Warden 635, Royal Champion 667, Lightning 700.
- Result: Return Home (601,573). A free chest can follow at home: tap (595,475) x4, Continue (595,578).
- A Mission Control flicker swallowed one click (screenshot showed Desktop 1-4 thumbnails); the next screenshot was normal. Just repeat the click.

## Seen 2026-11-27 06:21 (game area x 437-1048, y 195-475 = the 05:46 list above with x +141, y -142; worked all run)
- Offsets rule: read the game area's top-left from the first screenshot and shift a known list; every button below matched.
- Home: Battle (503,439) -> Find a Match (539,386) -> Attack! (933,439). Scout: Next (972,398); loot zoom (437,195)-(742,335). Full game zoom (437,195)-(1048,475): screen = 437 + zx*0.453, 195 + zy*0.454.
- Battle: pan drag (591,358)->(901,298). Left grass line about (585,262)->(708,380). Troop bar y=445: E-drag 576, balloons 607, barbarians 639, siege 679, King 712, Minion Prince 744, Warden 776, Royal Champion 808, Lightning 841. End Battle (505,406) -> Okay (787,364). Return Home (742,431).
- Free chest after a battle: tap (738,320) x4-5, Continue (737,436). Star Bonus dialog: Claim (742,408).
- Boat to the Builder Base: drag (640,390)->(900,230) twice, boat at about (703,232).
- Builder Base: Battle (503,439) -> Find Now! (859,372); troop bar y=445: Battle Machine 577, Baby Dragons 615/648/680/713; Return Home (742,428). Upgrades icon (968,411); list rows x=924 (first row y≈243, then ~261/280); tabs: builders (886,455), Star Lab (966,455); list X (998,205). Upgrade Confirm (743,418); research Confirm (861,429), then dialog X (898,213). Elixir Cart Collect (855,423), X (904,222).

## Seen 2026-11-18 11:00-11:22 (window NOT centered, worked fine all run: game area x 708-1320, y 444-724 = centered x +328, y +109)
- Connect card: "Try Again" at (849,677), then ~25 s to the village.
- Home: Battle (774,689); builder icon (1243,660) opens the list; list X (1270,454); rows at y≈528/548/588 (top), tabs: builders (1137,705), lab (1178,705), forge (1219,705), pets (1260,705).
- Upgrade dialog: green Confirm with resource icon (1112,680); grey Hammer button left of it (1035,680): never; dialog X (1199,463). New building: placement tick at about (970,580).
- Battle menu: Find a Match (811,636) -> army screen Attack! (1204,689). Scout: Next (1243,646) costs 1,500 gold; loot zoom (708,444)-(1014,584); 30 s timer then the battle auto-starts.
- Battle: the view starts zoomed in on the base centre. Drag (860,600)->(1180,560) to bring the left grass on screen, then deploy around (850-900, 540-620). Troop bar y=692: E-drag 855, Minion 885, Goblin 915, siege 950, King 984, Warden 1016, Lightning 1051, 2nd spell 1083. Scroll-wheel zoom out does not work.
- Result: Return Home / Claim Reward (1014,680). Chest: tap (1012,580) 4-5 times, Continue (1008,684) or (1018,691). After Claim Reward the game returns home by itself (a following tap on Battle can land on the chest screen: screenshot first).
- Builder tab counter "1/6" and lab "1/2" include the gem Goblin Builder/Researcher: with 5 job rows listed, no real builder is free.
