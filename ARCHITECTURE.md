# Canastra — Technical Architecture

> **Last updated:** Phase 2b complete (2026-04-22)
> **Status:** Pure domain package and deterministic game engine both shipped. Terminal CLI still runs via legacy shims; service/delivery layers pending.

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
| Determinism | Seeded RNG per game, replayable | ✅ shipped (Phase 2b) |
| Rules | Full canonical family variant | ✅ shipped (Phase 2a–2b) |

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
|  APPLICATION / GAME ENGINE   (Phase 2 — ✅ shipped)                   |
|    canastra/engine/engine.py    apply(state, action) → (state', events) |
|    canastra/engine/state.py     GameConfig, GameState, Meld, Phase    |
|    canastra/engine/actions.py   Draw, PickUpTrash, CreateMeld,        |
|                                 ExtendMeld, Discard, Chin             |
|    canastra/engine/events.py    CardDrawn, MeldCreated, MeldExtended, |
|                                 Discarded, TurnAdvanced, Chinned,     |
|                                 ReserveTaken, DeckReplenished,        |
|                                 TrashPickedUp, GameEnded              |
|    canastra/engine/scoring.py   end_of_game_score (+ card-removal)   |
|    canastra/engine/timer.py     forced_discard (priority ladder)      |
|    Deterministic + seeded RNG. Serializable state (pydantic v2).      |
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
├── canastra/                     # ★ pure package — Phase 1 + 2
│   ├── __init__.py
│   ├── domain/                   # Phase 1 — pure rules (no I/O, no state)
│   │   ├── __init__.py           # re-exports from cards/rules/scoring
│   │   ├── cards.py              # Card, Deck, Suit constants, SUITS tuple
│   │   ├── rules.py              # WILD_RANK, rank_to_number, is_in_order, is_clean, extends_set, is_permanent_dirty
│   │   └── scoring.py            # points_for_set (+ points_from_set legacy alias)
│   └── engine/                   # Phase 2b — deterministic state machine
│       ├── __init__.py           # public API: apply, initial_state, Action/Event types, GameConfig/GameState
│       ├── state.py              # GameConfig, Meld, TurnState, Phase, GameState (pydantic v2)
│       ├── actions.py            # Action discriminated union (Draw, PickUpTrash, CreateMeld, ExtendMeld, Discard, Chin)
│       ├── events.py             # Event discriminated union (CardDrawn, MeldCreated, ... GameEnded)
│       ├── errors.py             # ActionRejected
│       ├── setup.py              # initial_state(config) — seeded deal
│       ├── engine.py             # apply(state, action) → (state', events) + per-action handlers
│       ├── scoring.py            # end_of_game_score + card-removal greedy
│       └── timer.py              # forced_discard priority ladder for timer rule
│
├── deck.py                       # re-export shim → canastra.domain.cards  (Phase 3: delete)
├── helpers.py                    # re-export shim → canastra.domain.rules/scoring  (Phase 3: delete)
├── player.py                     # Player (legacy — mutates Table; replaced by engine)
├── table.py                      # Table (legacy — god object; replaced by engine state)
├── main.py                       # module-scope interactive loop (Phase 3: → thin CLI adapter over engine)
│
└── tests/
    ├── test_deck.py              # legacy unittest (verbatim, moved from test.deck.py)
    ├── test_helpers.py           # legacy unittest (verbatim, moved from test.helpers.py)
    ├── test_smoke.py             # import-time smoke for flat modules
    ├── domain/
    │   ├── __init__.py
    │   ├── test_cards.py         # deterministic + hypothesis invariants on Card / Deck
    │   ├── test_rules.py         # deterministic rules (all 5 Phase-2 xfails now passing)
    │   └── test_scoring.py       # points_for_set tiers
    └── engine/
        ├── __init__.py
        ├── conftest.py           # fixtures: cfg_4p2d, _hand_with, _advance_to_playing
        ├── test_state.py         # GameConfig + serialization invariants
        ├── test_setup.py         # initial_state determinism + shape
        ├── test_actions.py       # draw / pickup_trash / create_meld / extend_meld / discard
        ├── test_chin.py          # empty-hand reserve pickup + chin + game end
        ├── test_deck_exhaust.py  # deck-empty replenish from reserves
        ├── test_scoring.py       # end-of-game card-removal + bonus tally
        ├── test_timer.py         # forced-discard priority ladder
        └── test_replay.py        # seed + action log → deterministic final state
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
def is_permanent_dirty(cards: list[Card]) -> bool
```

**Rule coverage status** (canonical family variant fully implemented):

| Rule | Covered? | Where |
|---|---|---|
| Monotonic same-suit run | ✅ | `is_in_order` |
| Wild in interior slot | ✅ | `is_in_order` |
| Ace-low OR Ace-high | ✅ | `is_in_order` + `rank_to_number(high_ace=...)` |
| Ace-low + Ace-high (1000-pt canastra) | ✅ | `is_in_order` 14-card path |
| Clean canastra | ✅ | `is_clean` (≥ 7, natural-2 allowed in rank-2 slot, no other wilds) |
| Permanent-dirty detection | ✅ | `is_permanent_dirty` (wild-outside-2-slot or duplicate 2) |
| Wild reinterpretation on extend | ✅ | `extends_set` existential wild-assignment search |
| Max 2 wilds across suits | ✅ | `extends_set` + `is_in_order` wild cap |
| `extends_set` validates run structure | ✅ | `extends_set` enforces contiguous run |

### 4.3 `canastra.domain.scoring`

```python
def points_for_set(s: list[Card]) -> int
def points_from_set(s: list[Card]) -> int   # legacy alias — main.py calls this
```

Bonus tiers: 1000 (A-low + A-high, 14 cards) / 500 (2…A, 13 cards) / 200 (clean canastra, ≥ 7) / 100 (dirty canastra, ≥ 7) / 0 (shorter sets).

Table-card bonus (+10/card) is **not** computed here — that's an engine/game-end-scoring concern and will live in `canastra.engine.scoring` (Phase 2).

### 4.4 Legacy flat modules (`player.py`, `table.py`, `main.py`)

**Replaced by the `canastra.engine` package as of Phase 2b.** Treat as frozen — Phase 3 deletes them when `main.py` is rewired as a CLI adapter over the engine.

Known issues preserved from the original code:
- `Player.drop_set` / `can_extend_set` / `chin` / `remove_from_set` mutate `Table` state directly — violates layer boundaries.
- `Table._team_has_clean_canastra` (`table.py:69`) calls a non-existent method (`s._is_clean()`) — crashes if reached.
- `Table.__init__` assigns teams by `i % 2` index parity — reordering `players` scrambles teams.
- `main.py` inner-loop variable `i` shadows the outer turn index (`main.py:131`) — corrupts turn order after first meld.
- `main.py:286,294,295,320,328` — several scoring/input TypeErrors and a NameError (`points_from_set` now aliased in `scoring.py` to unblock the NameError, the rest remain).

### 4.5 `canastra.engine.state`

```python
TeamId = int
PlayerId = int

class GameConfig(BaseModel):          # frozen pydantic v2 model
    num_players: int                  # even, ≥ 4
    num_decks: int                    # ≥ 2
    reserves_per_team: int            # 2 ≤ x ≤ num_decks
    timer_enabled: bool = False
    seed: int                         # deterministic RNG seed

class Meld(BaseModel):
    id: UUID                          # stable identity across turns
    cards: list[Card]
    permanent_dirty: bool = False     # sticky once True

class Phase(str, Enum):
    WAITING_DRAW, PLAYING, ENDED

class TurnState(BaseModel):
    player_id: PlayerId
    phase: Phase

class GameState(BaseModel):
    config: GameConfig
    action_seq: int                   # increments on every successful apply()
    seat_order: list[PlayerId]
    teams: dict[TeamId, list[PlayerId]]
    hands: dict[PlayerId, list[Card]]
    melds: dict[TeamId, list[Meld]]
    reserves: dict[TeamId, list[list[Card]]]   # stack of reserve hands
    reserves_used: dict[TeamId, int]
    deck: list[Card]                           # draw pile; top = deck[-1]
    trash: list[Card]                          # discard pile
    current_turn: TurnState
    phase: Phase
    chin_team: TeamId | None = None
    winning_team: TeamId | None = None
```

All models are serializable to/from JSON via `model_dump_json` / `model_validate_json` for action-log replay and future WebSocket transport.

### 4.6 `canastra.engine.actions` and `canastra.engine.events`

Discriminated-union pydantic models. Actions are commands into `apply()`; events are the record emitted back.

```python
# actions.py
Action = Draw | PickUpTrash | CreateMeld | ExtendMeld | Discard | Chin

# events.py
Event = CardDrawn | MeldCreated | MeldExtended | Discarded | TurnAdvanced
      | TrashPickedUp | ReserveTaken | DeckReplenished | Chinned | GameEnded
```

`ActionRejected` (in `errors.py`) is raised synchronously for illegal actions — wrong turn, wrong phase, card not in hand, invalid run, etc. Callers decide whether to retry or escalate.

### 4.7 `canastra.engine.engine`

```python
def apply(state: GameState, action: Action) -> tuple[GameState, list[Event]]
```

Pure dispatcher. Per-action handlers are module-private (`_handle_draw`, `_handle_create_meld`, etc.). Every handler increments `action_seq`, returns a brand-new `GameState` via `model_copy`, and emits zero or more events. The empty-hand/reserve-pickup flow is routed through the shared `_try_empty_hand_resolve` helper from CreateMeld / ExtendMeld / Discard; deck-empty is handled by `_replenish_deck` inside `_handle_draw`.

### 4.8 `canastra.engine.scoring`

```python
@dataclass(frozen=True)
class ScoreBreakdown:
    leftover_debt: int
    canastra_bonus: int
    table_points: int
    reserve_bonus: int
    chin_bonus: int
    total: int

def end_of_game_score(state: GameState) -> dict[TeamId, ScoreBreakdown]
```

Greedy card-removal optimizer: absorb leftover debt (10 × cards-in-hand) by removing (or partially trimming) the cheapest non-canastra sets, then trimming canastras above length 7, then sacrificing whole canastras — but only when the sacrifice is rationally justified (remaining debt ≥ table value of the canastra). Final total floored at 0; bonuses are 100 per reserve used + 100 for the chin team.

### 4.9 `canastra.engine.timer` and `canastra.engine.setup`

- `setup.initial_state(config)` — seeded deal. RNG is `random.Random(config.seed)`; identical configs produce bit-identical states.
- `timer.forced_discard(state, player_id, rng)` — priority ladder for the optional 1-minute timer rule. Tiers 1–6 (duplicate-opponent-card → extend-permanent-dirty → ... → extend-clean-canastra → neutral), with a hard avoid on wilds and Aces unless the hand contains nothing else.

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

The Phase 2 to-do list was encoded as 5 `@pytest.mark.xfail(strict=True)` tests in `tests/domain/`. All 5 were resolved in Phase 2a — the markers are gone and the assertions are now live. Future phases may reintroduce xfail tests to pin upcoming specs; none are open today.

### 7.4 Coverage ratchet

| Phase | `fail_under` | Rationale |
|---|---|---|
| 0 | 0 (permissive baseline) | ✅ shipped |
| 1 | 0 (still permissive) | ✅ shipped at 64% actual |
| 2 | 80 | ✅ shipped at 82% actual (Phase 2b) |
| 3 | 85 | CLI thin; everything but the interactive wiring |
| 4 | 85 | HTTP + WS handlers excluded via pragma where appropriate |
| 5+ | 90 | Persistence + full stack |

Current coverage: **82%** (domain + engine both >80%; legacy `player.py`/`table.py`/`main.py` remain at 0% — they'll be deleted in Phase 3).

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
| 2 | Game engine state machine. Fix the 5 xfails. Implement wild-reinterpret, permanent-dirty, end-of-game scoring algorithm, timer rule, chin semantics | ✅ 2026-04-22 | `(state, action) → (state', events)` for a full game; chin + deck-exhaust + timer scenarios green |
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
