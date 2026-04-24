<div align="center">
  <h1 align="center">canastra</h1>
  <h3>A Python implementation of the family-variant Canasta card game.</h3>
</div>

<br/>

<div align="center">
  <a href="https://github.com/lucasluize-tech/canastra/stargazers"><img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/lucasluize-tech/canastra"></a>
  <a href="https://github.com/lucasluize-tech/canastra/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue"></a>
  <a href="https://github.com/lucasluize-tech/canastra/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/lucasluize-tech/canastra/ci.yml"></a>
</div>

<br/>

A terminal Canastra game built around a deterministic, replayable game engine. Implements the author's family rule variant (no jokers, no freeze, no black/red threes). The codebase is a layered architecture: a pure rules domain, a pydantic-modeled state machine engine, and a thin CLI on top — with a web-multiplayer layer planned for future phases.

## Features

- **Family Rule Variant:** Full canonical implementation of the author's family rules — wild reinterpretation, permanent-dirty detection, chin semantics, and the end-of-game card-removal scoring algorithm.
- **Deterministic Engine:** `apply(state, action) → (state', events)` — pure functions, seeded RNG, serializable pydantic v2 state. Replay any game from `(seed, action_log)`.
- **Configurable Setup:** Any even N ≥ 4 players, any number of decks ≥ 2, configurable reserve hands per team. No hardcoded 4-player/4-deck limit.
- **Multi-Team Scoring:** Greedy card-removal optimizer with rational-sacrifice guard — preserves canastras when sacrificing them would lose points.
- **Timer Rule (Optional):** Six-tier forced-discard priority ladder for time-limited play, with hard avoid on wilds and Aces.
- **Layered Architecture:** Pure domain → engine → delivery. Engine has zero I/O; ready to drop behind a FastAPI WebSocket layer.
- **Color-Coded Terminal Output:** Rich, color-coded display of hands, table sets, and turn state.

## Demo

```
$ python -m canastra
Number of players (must be even, >= 4): 4
Number of decks (>= 2): 2
Reserve hands per team (2 to num_decks): 2
Player 1 name: Alice
Player 2 name: Bob
Player 3 name: Carol
Player 4 name: Dave

== Alice's turn ==
Hand: 3♥ 5♥ 7♣ 9♦ J♠ Q♠ K♠ A♠ 2♥ 4♦ 6♣
Trash: (empty)

[d]raw / [t]rash / [p]lay / [x]discard / [q]uit:
```

## Tech Stack

- [Python 3.11+](https://www.python.org/) — Language
- [Pydantic v2](https://docs.pydantic.dev/) — State + action/event models
- [pytest](https://docs.pytest.org/) — Test runner
- [hypothesis](https://hypothesis.readthedocs.io/) — Property-based testing
- [ruff](https://docs.astral.sh/ruff/) — Linting & formatting
- [mypy](https://mypy-lang.org/) — Strict type checking on the domain + engine packages
- [uv](https://docs.astral.sh/uv/) — Package management
- [colored](https://pypi.org/project/colored/) — Terminal color output

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install from source

```shell
git clone https://github.com/lucasluize-tech/canastra.git
cd canastra
python -m venv venv
source venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt
```

### Run the game

```shell
python -m canastra
```

The CLI prompts for the number of players, decks, reserve hands per team, and player names — then drops you into the turn loop.

For reproducible games (useful for debugging or playtesting a specific shuffle), set the `CANASTRA_SEED` environment variable:

```shell
CANASTRA_SEED=42 python -m canastra
```

## Usage

### Playing a game

Each turn is a three-phase loop:

1. **Draw** — pull from the deck or pick up the entire trash pile.
2. **Play** — create a new meld, extend an existing one, or pass.
3. **Discard** — push one card onto the trash pile and pass to the next player.

Wild cards (rank `2`) can fill any slot in a same-suit run. A meld of length ≥ 7 is a *canastra*; length < 7 is a *short set*. The first team to "chin" — empty their hand with no reserves left and at least one clean canastra — ends the game.

For full rule details, see [`canastra/domain/rules.py`](canastra/domain/rules.py) and the in-tree [`ARCHITECTURE.md`](ARCHITECTURE.md).

### Programmatic engine usage

The engine is importable as a pure library:

```python
from canastra.engine import GameConfig, initial_state, apply, Draw, Discard

cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=42)
state = initial_state(cfg)

state, events = apply(state, Draw(player_id=0))
state, events = apply(state, Discard(player_id=0, card=state.hands[0][0]))
```

State is fully serializable via `state.model_dump_json()` and restorable via `GameState.model_validate_json(blob)` — so you can persist mid-game state and resume deterministically.

### Development

```shell
make ci             # lint + typecheck + tests
pytest              # full suite + coverage (config in pyproject.toml)
ruff check .        # lint
ruff format .       # format
mypy canastra/      # type check
```

## Project Structure

```
canastra/
├── canastra/
│   ├── __main__.py         # python -m canastra entry point
│   ├── domain/             # Pure rules — no I/O, no state
│   │   ├── cards.py        # Card, Deck, Suit constants
│   │   ├── rules.py        # is_in_order, is_clean, extends_set, is_permanent_dirty
│   │   └── scoring.py      # points_for_set
│   ├── engine/             # Deterministic state machine
│   │   ├── state.py        # GameConfig, GameState, Meld, Phase, TurnState (pydantic)
│   │   ├── actions.py      # Draw, PickUpTrash, CreateMeld, ExtendMeld, Discard, Chin
│   │   ├── events.py       # CardDrawn, MeldCreated, ..., GameEnded
│   │   ├── engine.py       # apply(state, action) → (state', events)
│   │   ├── scoring.py      # End-of-game card-removal optimizer
│   │   └── timer.py        # Forced-discard priority ladder
│   └── cli/                # Thin interactive adapter over the engine
│       ├── setup.py        # build_config_interactive (env-seed aware)
│       ├── prompts.py      # BadInput + pure parsers + ask_* reprompt wrappers
│       ├── render.py       # format_hand / format_table / format_events / format_score
│       └── loop.py         # run(), _do_draw_phase, _do_play_phase, _do_discard
├── tests/                  # 196 tests, 92% coverage (domain + engine + cli)
├── ARCHITECTURE.md         # Structural reference + phase status
└── pyproject.toml
```

## Roadmap

This project is being incrementally refactored into a web-multiplayer game. Phase status:

| Phase | Scope | Status |
|---|---|---|
| 0 | Test infrastructure | ✅ shipped |
| 1 | Pure domain package extraction | ✅ shipped |
| 2 | Game engine state machine | ✅ shipped |
| 3 | Thin CLI adapter (`python -m canastra`); legacy shims deleted | ✅ shipped |
| 4 | FastAPI HTTP + WebSocket multiplayer | ⏳ next |
| 5 | Postgres persistence (action log + snapshots) | ⏳ |
| 6 | Web frontend | ⏳ |

See [`ARCHITECTURE.md`](ARCHITECTURE.md) §10 for details.

## Acknowledgements

Big thanks 👏 to [Boot.dev](https://boot.dev) for making learning fun. This was the author's first Python project — see the [project history](https://github.com/lucasluize-tech/canastra/commits/main) for the journey from a flat-layout terminal game to a layered, type-checked, replayable engine.

## Contributing

Contributions are welcome. Fork the repository, make your changes, and open a pull request. Please ensure tests, lint, and type checks pass before submitting:

```shell
pytest
ruff check .
ruff format --check .
mypy canastra/
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
