# Canastra — Technical Architecture

> **Last updated:** Phase 1 complete (2026-04-18)
> **Status:** Terminal CLI functional via shims. Pure domain package extracted. Engine/service/delivery layers pending.

This document is the structural reference for the Canastra codebase. It is
updated at the end of every migration phase (see §10). For **rules**, see the
memory note `project_canastra_rules.md` (the canonical family variant). For
**migration plan details**, see `project_webmultiplayer_plan.md`.

---

## 1. Goals

| Dimension | Today | Target |
|---|---|---|
| Interface | Terminal (blocking stdin) | Web (WebSocket multiplayer + HTTP lobby) |
| Players | 2 teams × 2 players, hardcoded in `main.py` | Any even N ≥ 4, 2 teams of N/2 |
| Decks | 4 decks, hardcoded | Even N ≥ 2, configurable at game start |
| Reserves/team | 2, hardcoded | `2 ≤ x ≤ num_decks`, configurable |
| Persistence | None | Postgres (users, games, action log, snapshots) |
| Determinism | `random.shuffle` at import time | Seeded RNG per game, replayable |
| Rules | Legacy `helpers.py` (several gaps) | Full canonical family variant |

---

## 2. Target Layered Architecture

```
+-----------------------------------------------------------------------+
|  DELIVERY         (Phase 4+)                                          |
|    FastAPI — HTTP (/auth, /rooms, /history)                           |
|    FastAPI — WebSocket (/ws/room/{id})                                |
+-----------------------------------------------------------------------+
                 | Commands (JSON) ↑ / Events (JSON) ↓
                 v
+-----------------------------------------------------------------------+
|  TRANSPORT / SESSION   (Phase 4)                                      |
|    Connection registry   (user_id ↔ ws)                               |
|    Room manager           (create/join/ready/start/reconnect)         |
|    Auth middleware        (JWT / magic link)                          |
|    Command dispatcher     → engine                                    |
|    Event fan-out          (broadcast public, private hand views)      |
+-----------------------------------------------------------------------+
                 | Action (domain DTO)
                 v
+-----------------------------------------------------------------------+
|  APPLICATION / GAME ENGINE   (Phase 2)                                |
|    engine.apply(state, action) → (state', events)                     |
|    Turn state machine:                                                |
|       WaitingDraw → Playing → Discarding → End                        |
|    Action types: Draw, PickUpTrash, CreateMeld, ExtendMeld,           |
|                  Discard, Chin                                        |
|    Events:       CardDrawn, SetCreated, SetExtended, TurnEnded, ...   |
|    Deterministic + seeded RNG. Serializable state (pydantic).         |
|    Forbidden: I/O, sockets, DB, `print`, `input`.                     |
+-----------------------------------------------------------------------+
                 | uses pure functions
                 v
+-----------------------------------------------------------------------+
|  DOMAIN   (Phase 1 — ✅ shipped)                                      |
|    canastra/domain/cards.py     Card, Deck, Suit constants            |
|    canastra/domain/rules.py     is_in_order, is_clean, extends_set    |
|    canastra/domain/scoring.py   points_for_set, points_from_set       |
|    Pure functions / value objects. No I/O. Hypothesis-property-testable. |
+-----------------------------------------------------------------------+

+-----------------------------------------------------------------------+
|  PERSISTENCE   (Phase 5)                                              |
|    users            (Postgres)                                        |
|    rooms            (Redis hot state; Postgres archive)               |
|    games            (metadata)                                        |
|    action_log       (append-only; game_id, seq, json)                 |
|    snapshots        (state_json @ action_seq, for fast resume)        |
+-----------------------------------------------------------------------+
```

**Immutable rules:**
- Lower layers never import upper layers.
- Domain has zero framework dependencies (no FastAPI, no SQLAlchemy, no pydantic if it's not strictly needed).
- The engine is deterministic: `apply(state, action)` with the same seed and action log always yields the same state.
- Only the engine's emitted events cross the process boundary; raw state is never sent to clients (otherwise you leak hands).

---

## 3. Current Repository Layout

```
canastra/                         # repo root
├── ARCHITECTURE.md               # ← you are here
├── CLAUDE.md                     # harness instructions for Claude Code
├── README.md                     # player-facing rules + roadmap
├── Makefile                      # install-dev, lint, format, typecheck, test, ci
├── conftest.py                   # sys.path shim for flat-layout imports (DELETE in Phase 3)
├── pyproject.toml                # project metadata, ruff/pytest/coverage/mypy config
├── requirements.txt              # runtime deps (colored)
├── requirements-dev.txt          # pytest, hypothesis, ruff, mypy, pre-commit
├── .pre-commit-config.yaml       # fast hooks (ruff, whitespace, yaml/toml checks)
├── .github/workflows/ci.yml      # lint · typecheck · test matrix (py3.11 + py3.12)
│
├── canastra/                     # ★ pure package — Phase 1
│   ├── __init__.py
│   └── domain/
│       ├── __init__.py           # re-exports from cards/rules/scoring
│       ├── cards.py              # Card, Deck, Suit constants, SUITS tuple
│       ├── rules.py              # WILD_RANK, rank_to_number, is_in_order, is_clean, extends_set
│       └── scoring.py            # points_for_set (+ points_from_set legacy alias)
│
├── deck.py                       # re-export shim → canastra.domain.cards  (Phase 3: delete)
├── helpers.py                    # re-export shim → canastra.domain.rules/scoring  (Phase 3: delete)
├── player.py                     # Player (legacy — mutates Table; Phase 2: replaced by engine)
├── table.py                      # Table (legacy — god object; Phase 2: replaced by engine state)
├── main.py                       # module-scope interactive loop (Phase 3: → thin CLI adapter)
│
└── tests/
    ├── test_deck.py              # legacy unittest (verbatim, moved from test.deck.py)
    ├── test_helpers.py           # legacy unittest (verbatim, moved from test.helpers.py)
    ├── test_smoke.py             # import-time smoke for flat modules
    └── domain/
        ├── __init__.py
        ├── test_cards.py         # deterministic + hypothesis invariants on Card / Deck
        ├── test_rules.py         # deterministic rules + 4 xfail specs for Phase 2
        └── test_scoring.py       # points_for_set tiers + 1 xfail for A-low+A-high sort
```

**Files marked "Phase 3: delete":** after Phase 3 rewires `main.py` as a thin CLI adapter over the engine, `deck.py`, `helpers.py`, `player.py`, `table.py`, and the top-level `conftest.py` all disappear — the engine replaces them.

---

## 4. Module Reference (current state)

### 4.1 `canastra.domain.cards`

```python
Suit = str                        # alias for the 4 unicode glyphs
HEARTS, DIAMONDS, CLUBS, SPADES   # suit constants
SUITS: tuple[Suit, ...]           # canonical suit iteration order

class Card:
    suit: Suit
    rank: str | int               # "Ace" | 2..10 | "Jack" | "Queen" | "King"
    def __hash__(self) -> int     # NEW — was missing, made cards unhashable
    # __eq__, __lt__, __gt__ compare via (suit_order, rank_order)

class Deck:
    cards: list[Card]
    def _shuffle(rng: random.Random | None = None)   # injectable RNG
    def deal() -> Card
    def _deal_new_hands(n: int) -> list[list[Card]]
```

**Design notes.**
- `Card.__eq__` intentionally ignores deck identity — in multi-deck play, two `2♥` cards from different decks compare equal. `hand.remove(card)` removes the first match.
- `rank` is polymorphic (`str` for face cards + Ace, `int` for 2..10). A future refactor may normalize this to a dataclass-style enum, but doing so changes test fixtures everywhere — deferred.
- `rank_order["Ace"] == 1` permanently. Ace-high is handled by `rank_to_number(rank, high_ace=True)` in `rules.py`, NOT by mutating `Card`.

### 4.2 `canastra.domain.rules`

```python
WILD_RANK: int = 2                # the wildcard rank

def rank_to_number(rank, high_ace=False) -> int
def is_in_order(cards: list[Card]) -> bool
def is_clean(cards: list[Card]) -> bool
def extends_set(chosen_set: list[Card], card_list: list[Card]) -> bool
```

**Rule coverage status** (see canonical rules memo for full spec):

| Rule | Covered? | Where |
|---|---|---|
| Monotonic same-suit run | ✅ (basic cases) | `is_in_order` |
| Wild in interior slot | ✅ | `is_in_order` |
| Ace-low OR Ace-high | ✅ | `is_in_order` + `rank_to_number(high_ace=...)` |
| Ace-low + Ace-high (1000-pt canastra) | ❌ Phase 2 | xfail test pins the spec |
| Clean canastra | ✅ | `is_clean` (≥ 7, natural-2 allowed in rank-2 slot, no other wilds) |
| Permanent-dirty detection | ❌ Phase 2 | xfail test pins the spec |
| Wild reinterpretation on extend | ❌ Phase 2 | xfail test pins the spec |
| Max 2 wilds across suits | ❌ Phase 2 | xfail test pins the spec |
| `extends_set` validates run structure | ❌ Phase 2 | xfail test pins the spec |

### 4.3 `canastra.domain.scoring`

```python
def points_for_set(s: list[Card]) -> int
def points_from_set(s: list[Card]) -> int   # legacy alias — main.py calls this
```

Bonus tiers: 1000 (A-low + A-high, 14 cards) / 500 (2…A, 13 cards) / 200 (clean canastra, ≥ 7) / 100 (dirty canastra, ≥ 7) / 0 (shorter sets).

Table-card bonus (+10/card) is **not** computed here — that's an engine/game-end-scoring concern and will live in `canastra.engine.scoring` (Phase 2).

### 4.4 Legacy flat modules (`player.py`, `table.py`, `main.py`)

**Being replaced by the engine in Phase 2.** Treat as frozen — bug fixes only via the engine rewrite, not by editing these files directly.

Known issues preserved from the original code:
- `Player.drop_set` / `can_extend_set` / `chin` / `remove_from_set` mutate `Table` state directly — violates layer boundaries.
- `Table._team_has_clean_canastra` (`table.py:69`) calls a non-existent method (`s._is_clean()`) — crashes if reached.
- `Table.__init__` assigns teams by `i % 2` index parity — reordering `players` scrambles teams.
- `main.py` inner-loop variable `i` shadows the outer turn index (`main.py:131`) — corrupts turn order after first meld.
- `main.py:286,294,295,320,328` — several scoring/input TypeErrors and a NameError (`points_from_set` now aliased in `scoring.py` to unblock the NameError, the rest remain).

---

## 5. Data & State Model (current)

**Today, the "game state" is scattered across four objects:**

```
Table
├── deck:          Deck
├── new_hands:     list[list[Card]]         # reserves (mortos)
├── trash:         list[Card]
├── team1_sets:    dict[Suit, list[list[Card]]]
├── team2_sets:    dict[Suit, list[list[Card]]]
├── team1_hands:   int                      # reserve count consumed
├── team2_hands:   int
├── players:       list[Player]
├── team1:         list[Player]             # players with even index
├── team2:         list[Player]             # players with odd index
└── game_over:     bool

Player
├── name:  str
├── hand:  list[Card]
└── played: bool                            # set on first meld this turn
```

**Target engine state (Phase 2), serializable as JSON:**

```python
class GameState:
    config:        GameConfig          # num_players, num_decks, reserves_per_team, timer_enabled
    rng_seed:      int
    seat_order:    list[PlayerId]
    teams:         dict[TeamId, list[PlayerId]]
    hands:         dict[PlayerId, list[Card]]
    melds:         dict[TeamId, list[Meld]]       # Meld has stable UUID id
    reserves:      dict[TeamId, list[list[Card]]] # each team's reserve stack
    reserves_used: dict[TeamId, int]
    deck:          list[Card]
    trash:         list[Card]
    current_turn:  TurnState           # player, phase, deadline_at (for timer)
    phase:         Phase               # "waiting_draw" | "playing" | "discarding" | "ended"
    action_seq:    int
```

Each `Meld` carries a stable id, its cards, and a `permanent_dirty: bool` flag — critical for scoring and for client animations that reference specific melds.

---

## 6. Data Flow

### 6.1 Today (terminal)

```
stdin → input()  ┐
                 ├──→  main.py loop  ──→  Player.drop_set / can_extend_set
deck.py          │                         │
helpers.py       │                         ▼
                 │                       Table state (mutated in place)
print()  ←───────┘                         │
                                           ▼
                                       stdout via color-coded print()
```

Rule checks live inside the input-validation loop; there is no pure boundary.

### 6.2 Target (web)

```
Browser ──WS──▶  FastAPI WS endpoint
                      │
                      ▼
                 RoomManager.submit(room_id, user_id, action_json)
                      │
                      ▼
                 GameService.apply(action)           ◀── validates auth/turn
                      │
                      ▼
                 engine.apply(state, action) → (state', events)
                      │
                      ▼
                 persist: append action_log, maybe snapshot
                      │
                      ▼
                 EventFanout.broadcast(events)       ──▶ room members
                 EventFanout.private(hand_events)    ──▶ owning player only
```

Each browser's UI state is a pure function of the events it has received. Replay = reapply actions to initial state.

---

## 7. Testing

### 7.1 Layout

```
tests/
├── test_deck.py, test_helpers.py   legacy — verbatim unittest, flat-module imports
├── test_smoke.py                   import-time regression guard
└── domain/
    ├── test_cards.py               hypothesis + deterministic on Card/Deck
    ├── test_rules.py               deterministic rule specs (+ xfail for Phase 2)
    └── test_scoring.py             scoring tiers (+ xfail for 1000-pt edge)
```

### 7.2 Test kinds

| Kind | Location | Tool | Role |
|---|---|---|---|
| Unit (deterministic) | `tests/domain/` | pytest | Pin specific rule outputs |
| Property | `tests/domain/test_cards.py` | hypothesis | Card invariants (ordering symmetry, etc.) |
| Smoke | `tests/test_smoke.py` | pytest | Import-time guard across refactors |
| Scenario (engine) | **Phase 2** | pytest | `(initial_state, action_log) → final_state` |
| Integration (WS) | **Phase 4** | pytest-asyncio + TestClient | Full room flows |
| Legacy regression | `test_deck.py`, `test_helpers.py` | unittest | Existing coverage |

### 7.3 `xfail` as spec

Phase 2 work is documented by `@pytest.mark.xfail(strict=True)` tests. `strict=True` means the test **fails if it unexpectedly passes** — so when Phase 2 implements the missing behavior, those tests flip to "unexpectedly passing" and force me to remove the marker. The xfail list IS the Phase 2 to-do.

Current xfails (5):
1. `test_ace_low_plus_ace_high_14_card` — `is_in_order` rejects the 14-card canastra
2. `test_permanent_dirty_wrong_suit_two` — `is_clean` doesn't detect permanent-dirty
3. `test_extends_rejects_non_run_extension` — `extends_set` ignores run structure
4. `test_rejects_third_wild_from_any_suit` — `extends_set` under-caps wilds
5. `test_ace_low_plus_ace_high_1000` — `points_for_set` positional check without sort

### 7.4 Coverage ratchet

| Phase | `fail_under` | Rationale |
|---|---|---|
| 0 | 0 (permissive baseline) | ✅ shipped |
| 1 | 0 (still permissive) | ✅ shipped at 64% actual |
| 2 | 60 | Engine + domain fully under test |
| 3 | 75 | CLI thin; everything but the interactive wiring |
| 4 | 80 | HTTP + WS handlers excluded via pragma where appropriate |
| 5+ | 85 | Persistence + full stack |

Current coverage: **64%** (`canastra.domain` is 95%+; legacy `player.py`/`table.py` pull the average down).

---

## 8. Tooling & Pipeline

### 8.1 Local loop

```
source venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt
uv pip install -e .
make hooks          # one-time: install pre-commit
make ci             # lint + typecheck + tests locally
```

### 8.2 Pre-commit (fast, on `git commit`)

- `ruff` (lint, `--fix`) + `ruff-format`
- `trailing-whitespace`, `end-of-file-fixer`, `check-added-large-files` (500 KB cap), `check-yaml`, `check-toml`, `check-merge-conflict`, `mixed-line-ending`

### 8.3 CI (GitHub Actions, `.github/workflows/ci.yml`)

Three parallel jobs on every push/PR to `main`:

1. **lint** — `ruff check .` + `ruff format --check .`
2. **typecheck** — `mypy` (strict on `canastra.domain.*`, lenient on legacy flat modules)
3. **test** — `pytest` on matrix `[py3.11, py3.12]`, uploads `coverage.xml` as artifact

TODO comments in `ci.yml` sketch the Phase 4 (API integration + Postgres service) and Phase 4+ (Docker build + push on tag) jobs — add them when their layers land.

### 8.4 Dev tools

| Tool | Role | Config |
|---|---|---|
| `ruff` | lint + format | `pyproject.toml` `[tool.ruff]` — line 100, E/F/I/B/UP/SIM/C4/W |
| `mypy` | typecheck | `pyproject.toml` `[tool.mypy]` — strict override on `canastra.domain.*` |
| `pytest` | test runner | `pyproject.toml` `[tool.pytest.ini_options]` — importlib mode, `tests/` |
| `pytest-cov` | coverage | branch coverage on, xml + term-missing reports |
| `hypothesis` | property tests | default profile |
| `pre-commit` | git hook | `.pre-commit-config.yaml` |
| `uv` | fast pip | local installs only; CI uses plain pip |

---

## 9. Known Gotchas

- **`Card.__eq__` ignores deck identity.** Intended for multi-deck play; `hand.remove(card)` picks the first structural match. Do not "fix" this without auditing every `.remove` call site.
- **`rank` is polymorphic (`str | int`).** `rank_order[rank]` works either way because the dict has both kinds of keys. Printing uses whatever type got constructed.
- **Teams in the legacy `Table` are assigned by `i % 2`.** Do not reorder `players` without updating `table.py` and `main.py` together.
- **`main.py` is module-scope code, not a function.** Importing it will immediately prompt for player names. Do not import it from tests or other modules until Phase 3.
- **`conftest.py` sys.path shim.** Needed today so `from deck import ...` works under pytest's `--import-mode=importlib`. Delete in Phase 3 once every caller imports from `canastra.*`.
- **`points_from_set` is a legacy alias.** `main.py:320,328` still uses the misspelled name. Do not rename `points_for_set` without also dropping the alias and updating callers.

---

## 10. Phase Status

| Phase | Scope | Status | Exit criterion |
|---|---|---|---|
| 0 | Test infra — rename dotted files, add pytest, tests/ dir, smoke test | ✅ 2026-04-17 | `pytest` runs + 10 tests pass |
| 1 | Extract pure domain → `canastra/domain/`, add property tests, xfail Phase 2 specs | ✅ 2026-04-18 | `canastra.domain.*` clean under ruff + mypy strict; 44 pass / 5 xfail |
| 2 | Game engine state machine. Fix the 5 xfails. Implement wild-reinterpret, permanent-dirty, end-of-game scoring algorithm, timer rule, chin semantics | ⏳ next | `(state, action) → (state', events)` for a full game; chin + deck-exhaust + timer scenarios green |
| 3 | Rewrite `main.py` as thin CLI adapter over engine; delete legacy shims + `Player`/`Table` + `conftest.py`. Game loop becomes a function. | ⏳ | `python -m canastra` plays end-to-end; no module-scope I/O |
| 4 | FastAPI HTTP + WebSockets. RoomManager, auth (magic link), private hand broadcasting, reconnect via snapshot replay. | ⏳ | Two browser tabs play a full game over WS |
| 5 | Postgres persistence: users, games, append-only `action_log`, periodic `snapshots`. | ⏳ | Server restart mid-game → clients reconnect and resume |
| 6 | Frontend (web client). Event-stream-driven UI. | ⏳ | Family plays a real game |
| 7 | Hardening: N-player generalization (currently 4 is the only fully-tested path), spectators, AFK timeouts, rate limiting. | ⏳ | 6p/6d and 8p/6d games complete without regressions |

### How to update this doc

At the end of each phase:
1. Flip the phase row's status to ✅ with the completion date.
2. Update §3 (layout) and §4 (module reference) to match what shipped.
3. Update §7 coverage ratchet row with actual coverage.
4. Move any remaining xfail entries to the right phase in §7.3.
5. Sync the "Last updated" header at the top.

---

## 11. References

- `README.md` — player-facing rules (may lag this document)
- `CLAUDE.md` — harness instructions for Claude Code (commands, conventions, gotchas)
- `project_canastra_rules.md` — canonical family rules (memory note; authoritative)
- `project_webmultiplayer_plan.md` — full 7-phase migration plan (memory note)
- `Makefile` — every supported command
- `.github/workflows/ci.yml` — what runs on every push
