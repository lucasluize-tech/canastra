# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Terminal-based Python implementation of Canastra (the author's family variant — no jokers, no freeze, no black/red threes). Rule nuances are documented in `README.md` and should be consulted before changing scoring or set-validation logic.

## Commands

```bash
pip install -r requirements.txt    # only dep: colored==2.2.3
python main.py                     # run the game (prompts for player names)
python test.deck.py                # deck/table unit tests
python test.helpers.py             # rule-logic unit tests (is_in_order, is_clean, extends_set, points_for_set)
```

Test files use dots in their names (`test.deck.py`, not `test_deck.py`), so `python -m unittest discover` and pytest auto-discovery will not pick them up — invoke each file directly. To run a single test: `python test.helpers.py TestHelpers.test_is_clean`.

## Architecture

Four modules plus a top-level game loop. Data flows one way: `main.py` drives input → mutates `Player` and `Table` state → delegates rule checks to `helpers.py`.

- **`deck.py`** — `Card` and `Deck`. `Card` defines ordering via `(suit_order, rank_order)`, so `sorted(hand)` groups by suit then rank. `Deck._deal_new_hands(n)` pops 11 cards × n into separate lists — used for both initial hands and the reserve "new hands" (mortos).
- **`player.py`** — `Player` owns a hand and per-turn `played` flag. `_is_play_valid` enforces suit/wildcard rules; `drop_set` / `can_extend_set` mutate the team's sets on the `Table`. `chin` handles the "hand empty" branch: pulls a new hand from `game.new_hands` or ends the game if the team already used both.
- **`table.py`** — `Table` is the game state: two teams (assembled by splitting `players` on even/odd index), per-team sets (`{suit: [set, set, ...]}`), per-team hand count, trash, deck, reserve hands. `_get_team_set(player)` is the canonical way to reach a player's team's sets.
- **`helpers.py`** — Pure functions for rule logic. Wildcard = rank `2`. `is_in_order` is the trickiest: it handles `2` as a positional wild and toggles `high_ace` based on whether the run ends at King/Queen. `is_clean` requires length ≥ 7 and at most one `2`, only in the "twos" position (i.e. natural run or `A,2,3,...`). `points_for_set` returns 1000/500/200/100 by canastra type.
- **`main.py`** — Not a function; the file is the game loop at module scope. Three-phase turn (draw → play loop → discard), with team color-coding (yellow = team1, blue = team2). After `game.game_over`, the post-game block subtracts remaining-hand cards from the table and tallies points.

## Conventions and gotchas

- Teams are assigned by index parity in `Table.__init__` — reordering `players` changes team composition. `main.py` also uses `i % 2` for the turn-color heuristic, which assumes that ordering.
- Suits are unicode glyphs (`♥ ♦ ♣ ♠`) defined at the top of `deck.py`, `player.py`, and `test.helpers.py`. Keep them consistent if adding files.
- `Card.__eq__` compares by `(suit, rank)` only, so duplicates across decks compare equal — `hand.remove(card)` removes the first match, which is the intended behavior for multi-deck play.
- Rank `2` is a wildcard everywhere except when it appears in the "twos" slot of a natural run. Touch `is_in_order` / `is_clean` / `extends_set` together when changing wildcard semantics — the test suite covers the tricky Ace-high/Ace-low and joker-in-middle cases.
- `README.md` lists the roadmap (API + frontend). Current code is strictly terminal/backend; there is no web layer yet.
