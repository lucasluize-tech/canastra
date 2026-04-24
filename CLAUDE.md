# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Terminal-based Python implementation of Canastra (the author's family variant — no jokers, no freeze, no black/red threes). Rule nuances are documented in `README.md` and `ARCHITECTURE.md` and should be consulted before changing scoring or set-validation logic.

## Commands

```bash
source venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt   # runtime + dev deps
python -m canastra                                           # run the game (prompts for player names)
CANASTRA_SEED=42 python -m canastra                          # reproducible shuffle for debugging
pytest                                                       # full suite + coverage (config in pyproject.toml)
pytest tests/cli -v                                          # just the CLI-layer tests
pytest tests/engine/test_apply.py::test_draw_from_deck       # single test
make ci                                                      # lint + typecheck + test locally
```

Tests live under `tests/` organized by layer: `tests/domain/`, `tests/engine/`, `tests/cli/`. Coverage floor is 85% across `canastra/`.

## Architecture

Three-layer stack, each layer depending only on the layer below it:

```
canastra/cli/     →  canastra/engine/  →  canastra/domain/
(interactive)       (state machine)      (pure rules)
```

- **`canastra/domain/`** — Pure rules. `cards.py` defines `Card`, `Deck`, and suit glyphs. `rules.py` owns wildcard semantics (`is_in_order`, `is_clean`, `extends_set`, `is_permanent_dirty`). `scoring.py` has `points_for_set`. No I/O, no state, mypy-strict.
- **`canastra/engine/`** — Deterministic state machine. `GameState` / `GameConfig` / `Meld` / `Phase` / `TurnState` are frozen pydantic v2 models. `apply(state, action) → (state', events)` is the pure transition function — everything else is helpers, validators, or the forced-discard timer ladder. Seeded shuffle makes `(seed, action_log) → replay` exact.
- **`canastra/cli/`** — Thin interactive adapter. `loop.run()` builds a `GameConfig` via `setup.build_config_interactive`, then dispatches on `state.current_turn.phase` through `_do_draw_phase` / `_do_play_phase` / `_do_discard`. All I/O is routed through injected `input_fn` / `output_fn` callables, so tests script input lists without touching stdin. Render functions (`format_hand`, `format_table`, `format_events`, `format_score`, `format_error`) are pure string builders.
- **`canastra/__main__.py`** — Five-line entry point: `raise SystemExit(run())`.

## Conventions and gotchas

- Teams are assigned by seat parity in `initial_state` — reordering `seat_order` changes team composition. Render functions use `{0: Fore.yellow, 1: Fore.blue}` for the two teams.
- Suits are unicode glyphs (`♥ ♦ ♣ ♠`) defined in `canastra/domain/cards.py`. Keep them consistent if adding files.
- `Card.__eq__` compares by `(suit, rank)` only, so duplicates across decks compare equal — `hand.remove(card)` removes the first match, which is the intended behavior for multi-deck play.
- Rank `2` is a wildcard everywhere except when it appears in the "twos" slot of a natural run. Touch `is_in_order` / `is_clean` / `extends_set` together when changing wildcard semantics — the domain test suite covers the tricky Ace-high/Ace-low and joker-in-middle cases.
- `GameState` is frozen; use `state.model_copy(update={...})` to derive a new state. The engine never mutates — every `apply` returns a fresh state.
- Engine actions raise `ActionRejected(str)` on illegal moves; CLI helpers catch and re-prompt. Do not let engine errors escape into the loop.
- `CANASTRA_SEED` env var overrides the random seed in `setup.build_config_interactive` — useful for reproducible debugging and scripted integration tests.
- `README.md` lists the roadmap (FastAPI + web frontend). Phase 3 shipped the CLI adapter; Phase 4 will introduce a WebSocket layer that swaps `input_fn`/`output_fn` for network I/O while the engine stays identical.
