# Contributing

Thanks for helping make coc-agent useful for more players. Please read the [disclaimer](README.md#disclaimer)
first: contributions that read game memory, intercept traffic, inject code, evade detection, or spend real money
won't be accepted.

## Run the tests

```bash
python3 -m unittest discover -s tests -v     # no Mac, iPhone or Claude needed
bash -n bin/cocctl
```

CI runs the same on macOS (Python 3.9 and 3.13) and Linux.

## Add a strategy profile

A profile is two files in `app/profiles/`:

- `<name>.json`: `summary` (one line), `best_for` (one line) and `config`, an overlay on
  `app/config.default.json`. Usually only `game` knobs; it can also set `game_limits` defaults or scheduler keys
  (`max_runs_per_day`, `min_interval_minutes`, ...). Only use keys that exist in the defaults (the tests check),
  except new `game` knobs, which are fine (e.g. `max_heroes_upgrading`).
- `<name>.md`: the direction the agent reads every run. Write it like you'd brief a strong player who has never
  seen the account: the goal, the priorities in order, the economy rule, when to upgrade the Town Hall, and what
  *not* to do. Keep it under one screen. Reference knobs by name so the agent can tune them.

Then `python3 -m unittest discover -s tests` and try it: `cocctl profile show <name>`.

## Improve the knowledge base

`app/knowledge/` is general Clash of Clans know-how, read by the agent on every account. Good additions are:

- **principles** that hold across Town Halls and game updates,
- **attack recipes** (`attacks.md`): name, Town Hall range, army, deploy steps, failure modes. Prefer simple,
  one-side deployments; a vision agent executes those far more reliably than precise multi-step funnels,
- corrections when a game update changed something. Mark version-sensitive numbers "verify in game".

Don't put one account's details there; those belong in that account's `memory/`.

## Change the agent's protocol

`app/CLAUDE.md` is the run protocol. Keep the hard rules intact and keep it account-agnostic. If you add a `coc`
command for the agent, add it to the docstring in `app/tools/coc.py`, the Tools section of CLAUDE.md, and a test.

## Ideas

See [docs/ROADMAP.md](docs/ROADMAP.md) for the planned improvements, with where each one goes in the code.
