# Canastra — Technical Architecture

> **Last updated:** Phase 4 complete (2026-04-28)
> **Status:** Pure domain package, deterministic engine, thin CLI adapter, and FastAPI WebSocket delivery layer all shipped. Persistence pending (Phase 5).

This document is the structural reference for the Canastra codebase. It is
updated at the end of every migration phase (see §10). For **rules**, see the
memory note `project_canastra_rules.md` (the canonical family variant). For
**migration plan details**, see `project_webmultiplayer_plan.md`.

---

## 1. Goals

| Dimension | Today | Target |
|---|---|---|
| Interface | Terminal (blocking stdin) | Web (WebSocket multiplayer + HTTP lobby) |
| Players | Configurable via `canastra.cli.setup` prompts + `canastra.engine.setup.initial_state` | Any even N ≥ 4, 2 teams of N/2 |
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
├── pyproject.toml                # project metadata, ruff/pytest/coverage/mypy config
├── requirements.txt              # runtime deps (colored)
├── requirements-dev.txt          # pytest, hypothesis, ruff, mypy, pre-commit
├── .pre-commit-config.yaml       # fast hooks (ruff, whitespace, yaml/toml checks)
├── .github/workflows/ci.yml      # lint · typecheck · test matrix (py3.11 + py3.12)
│
├── canastra/                     # ★ pure package — Phase 1 + 2 + 3
│   ├── __init__.py
│   ├── __main__.py               # python -m canastra entry point — `raise SystemExit(run())`
│   ├── domain/                   # Phase 1 — pure rules (no I/O, no state)
│   │   ├── __init__.py           # re-exports from cards/rules/scoring
│   │   ├── cards.py              # Card, Deck, Suit constants, SUITS tuple
│   │   ├── rules.py              # WILD_RANK, rank_to_number, is_in_order, is_clean, extends_set, is_permanent_dirty
│   │   └── scoring.py            # points_for_set (+ points_from_set legacy alias)
│   ├── engine/                   # Phase 2b — deterministic state machine
│   │   ├── __init__.py           # public API: apply, initial_state, Action/Event types, GameConfig/GameState
│   │   ├── state.py              # GameConfig, Meld, TurnState, Phase, GameState (pydantic v2)
│   │   ├── actions.py            # Action discriminated union (Draw, PickUpTrash, CreateMeld, ExtendMeld, Discard, Chin)
│   │   ├── events.py             # Event discriminated union (CardDrawn, MeldCreated, ... GameEnded)
│   │   ├── errors.py             # ActionRejected
│   │   ├── setup.py              # initial_state(config) — seeded deal
│   │   ├── engine.py             # apply(state, action) → (state', events) + per-action handlers
│   │   ├── scoring.py            # end_of_game_score + card-removal greedy
│   │   └── timer.py              # forced_discard priority ladder for timer rule
│   ├── cli/                      # Phase 3 — thin interactive adapter over engine
│   │   ├── __init__.py           # exports run
│   │   ├── setup.py              # build_config_interactive — prompts → (GameConfig, names)
│   │   ├── prompts.py            # BadInput + parse_* + ask_* wrappers
│   │   ├── render.py             # format_hand / _table / _events / _score / _error
│   │   └── loop.py               # run() + _do_draw_phase / _do_play_phase / _do_discard
│   └── web/                      # Phase 4 — FastAPI HTTP + WebSocket delivery
│       ├── __init__.py
│       ├── app.py                # create_app factory + lifespan-managed RoomManager
│       ├── codes.py              # Crockford-Base32 6-char room-code generator
│       ├── session.py            # SessionStore + signed-cookie helpers + SessionBinding
│       ├── messages.py           # ClientEnvelope / ServerEnvelope discriminated unions
│       ├── rooms.py              # Room + RoomManager + fanout + AFK timer + lobby grace
│       ├── http_routes.py        # POST /rooms · POST /rooms/{code} · GET /rooms/{code} · GET /
│       ├── ws_routes.py          # /ws/room/{code} — receive loop + dispatch
│       └── static/index.html     # vanilla-JS test harness (deleted in Phase 6)
│
└── tests/
    ├── domain/
    │   ├── __init__.py
    │   ├── test_cards.py         # deterministic + hypothesis invariants on Card / Deck
    │   ├── test_rules.py         # deterministic rules (all 5 Phase-2 xfails now passing)
    │   └── test_scoring.py       # points_for_set tiers
    ├── engine/
    │   ├── __init__.py
    │   ├── conftest.py           # fixtures: cfg_4p2d, _hand_with, _advance_to_playing
    │   ├── test_state.py         # GameConfig + serialization invariants
    │   ├── test_setup.py         # initial_state determinism + shape
    │   ├── test_actions.py       # draw / pickup_trash / create_meld / extend_meld / discard
    │   ├── test_chin.py          # empty-hand reserve pickup + chin + game end
    │   ├── test_deck_exhaust.py  # deck-empty replenish from reserves
    │   ├── test_scoring.py       # end-of-game card-removal + bonus tally
    │   ├── test_timer.py         # forced-discard priority ladder
    │   └── test_replay.py        # seed + action log → deterministic final state
    ├── cli/
    │   ├── test_scaffold.py      # package import sanity
    │   ├── test_prompts.py       # parse_* (BadInput cases) + ask_* reprompt loops
    │   ├── test_render.py        # format_hand / _table / _events / _score / _error
    │   ├── test_setup.py         # build_config_interactive prompts + CANASTRA_SEED env
    │   ├── test_loop.py          # run() phase dispatch + EOF → 130 + scripted game
    │   └── test_main_module.py   # `python -m canastra` subprocess smoke
    └── web/                      # Phase 4 — FastAPI/WebSocket integration tests
        ├── test_messages.py          # envelope round-trip
        ├── test_messages_property.py # Hypothesis envelope round-trip
        ├── test_messages_fuzz.py     # random JSON → only ValidationError allowed
        ├── test_http.py              # POST /rooms · POST /rooms/{code} · GET /rooms/{code}
        ├── test_ws_happy.py          # welcome / lobby_update / cookie auth
        ├── test_reconnect.py         # cookie-bound reconnect → Snapshot(reason="reconnect")
        ├── test_timer.py             # AFK timer → forced_discard
        ├── test_lobby_grace.py       # host-disconnect grace timer
        ├── test_backpressure.py      # slow client dropped, room continues
        ├── test_ws_adversarial.py    # 9 unhappy paths (rejection / origin / idempotency)
        ├── test_ws_races.py          # spec §11.2 races
        ├── test_replay_determinism.py # engine.apply outside the WS layer
        ├── test_concurrency.py       # static guard: Room.submit has no `await`
        └── test_shutdown.py          # lifespan teardown drops rooms cleanly
```

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
def points_from_set(s: list[Card]) -> int   # legacy alias kept for backward compat
```

Bonus tiers: 1000 (A-low + A-high, 14 cards) / 500 (2…A, 13 cards) / 200 (clean canastra, ≥ 7) / 100 (dirty canastra, ≥ 7) / 0 (shorter sets).

Table-card bonus (+10/card) is **not** computed here — that's an engine/game-end-scoring concern and will live in `canastra.engine.scoring` (Phase 2).

### 4.4 Legacy flat modules — **deleted in Phase 3**

The former flat-layout modules (`main.py`, `deck.py`, `helpers.py`, `player.py`, `table.py`) and the root `conftest.py` sys.path shim were removed in Phase 3 once `canastra.cli` became the only interactive entry point. See §4.10 for the replacement and §10 for the phase log.

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

### 4.10 `canastra.cli`

Interactive terminal adapter over `canastra.engine` — translates user input into engine actions and engine events into rendered output. Holds no game logic of its own; every rule decision is delegated to `engine.apply`.

- **`setup.py`** — `build_config_interactive(*, input_fn, output_fn) -> (GameConfig, list[str])`. Prompts for `num_players` (1–32), `num_decks` (1–16), `reserves_per_team` (1–16), and a name per player. Empty name falls back to `Player{i+1}`. Seed is read from `CANASTRA_SEED` env var or drawn at random.
- **`prompts.py`** — `BadInput` exception, pure parsers (`parse_card_indices`, `parse_yes_no`, `parse_choice`, `parse_int_in_range`), and interactive reprompt-loop wrappers (`ask_choice`, `ask_yes_no`, `ask_int_in_range`, `ask_card_indices`). Every wrapper takes injected `input_fn`/`output_fn` callables; parsers stay pure and raise `BadInput` on any invalid input.
- **`render.py`** — Pure formatters with no I/O: `format_hand`, `format_error`, `format_events` (covers all 10 engine events, including the silent `TurnAdvanced`), `format_table`, `format_score`. Team colors are `{0: Fore.yellow, 1: Fore.blue}`.
- **`loop.py`** — `run(*, input_fn=input, output_fn=print) -> int`. Returns `0` on normal end-of-game, `130` on `EOFError` / `KeyboardInterrupt`. Phase-dispatched turn loop via `_do_draw_phase`, `_do_play_phase` (which loops internally on bad input and returns `"meld"` or `"discard_requested"`), and `_do_discard` (returns `(state, events) | None`, where `None` means the user cancelled the discard and returns to the play phase). Helpers print events via `format_events` internally; `run()` stays a pure phase dispatcher.
- **`__main__.py`** — 5-line entry point: `raise SystemExit(run())`.

**Contract:** `run(input_fn, output_fn) → int`, exit code `0` on normal end-of-game, `130` on EOF. Every I/O is routed through the injected callables so tests use scripted input lists without monkeypatching `stdin`/`stdout`.

### 4.11 `canastra.web`

FastAPI HTTP + WebSocket delivery layer over `canastra.engine`. The engine remains pure — `web/` translates JSON commands into engine actions and engine events into JSON output without ever leaking private cards across audiences.

- **`app.py`** — `create_app(*, debug=False) -> FastAPI`. Asserts `CANASTRA_SESSION_SECRET` (≥ 32 bytes) and `WEB_CONCURRENCY=1` in non-debug. Lifespan creates a `RoomManager` and tears it down (cancel timer + lobby-grace tasks → broadcast `RoomClosed("server_shutdown")` → `ws.close(1001)` → drop rooms) inside `asyncio.wait_for(timeout=5.0)`.
- **`codes.py`** — Crockford Base32 (`0-9A-Z` minus `I/L/O/U`); 6-char codes; `RoomManager` retries on collision.
- **`session.py`** — opaque `session_id` via `secrets.token_urlsafe(32)`; `SessionBinding` is a dataclass holding `ws`, `ws_lock` (asyncio.Lock), and `recent_results` (idempotency cache, 64-entry bound). Cookie sign/verify via `itsdangerous.URLSafeTimedSerializer`.
- **`messages.py`** — `ClientEnvelope` + `ServerEnvelope` carrying `v: 1` and a discriminated-union inner `msg`. Client: `StartGame | SubmitAction | Rematch | LeaveRoom | RequestSnapshot | Ping`. Server: `Welcome | LobbyUpdate | Snapshot | EventMsg | Accepted | Rejected | DeadlineWarning | RoomClosed | Heartbeat | Pong`. `Rejected.reason` and `RoomClosed.reason` are `Literal` enums.
- **`rooms.py`** — `Room.submit(action)` is the synchronous read-modify-write chokepoint (no `await` between read and write of `state`); `Room.fanout` filters by `Event.audience` and applies a per-send `asyncio.wait_for` timeout that drops slow clients via `_mark_dead`. AFK timer is per-room with a `deadline_changed: asyncio.Event` to avoid tight loops. Lobby grace task cancels on host reconnect.
- **`http_routes.py`** — All "unknown room / full / started" paths return identical `404 {"error":"unavailable"}` to prevent code enumeration.
- **`ws_routes.py`** — Origin allowlist, signed-cookie verification, per-session `ws_lock` for the reconnect-swap, and dispatch for every `ClientMsg` type. Server overwrites `action.player_id` with `binding.seat` before passing to the engine so a malicious client can't impersonate another seat.

**Key invariants:**

- Engine never imports from `web/`.
- Private cards never leak: `Event.audience` and `GameState.view_for(seat)` own redaction.
- `Room.submit` is sync end-to-end; atomicity is asserted by `tests/web/test_concurrency.py`.

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
input_fn ──▶  cli.loop.run()
                   │
                   ▼
              _do_draw_phase / _do_play_phase / _do_discard
                   │                       ▲
                   │ Action                │ (state', events)
                   ▼                       │
              engine.apply(state, action) ─┘
                   │
                   │ events
                   ▼
              cli.render.format_events / _hand / _table / _score / _error
                   │
                   ▼
              output_fn
```

All rule logic lives inside `engine.apply`; the CLI only parses input, dispatches actions, and renders events. Both `input_fn` and `output_fn` are injected, so tests drive `run()` with scripted input lists and no stdin monkeypatching.

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
├── domain/                         deterministic + hypothesis rule tests
├── engine/                         scenario tests over (initial_state, action_log) → final_state
└── cli/                            adapter tests: parsers, renderers, scripted run() playthroughs
```

### 7.2 Test kinds

| Kind | Location | Tool | Role |
|---|---|---|---|
| Unit (deterministic) | `tests/domain/` | pytest | Pin specific rule outputs |
| Property | `tests/domain/test_cards.py` | hypothesis | Card invariants (ordering symmetry, etc.) |
| Scenario (engine) | `tests/engine/` | pytest | `(initial_state, action_log) → final_state` |
| CLI adapter | `tests/cli/` | pytest | Scripted `input_fn` lists drive `run()` end-to-end |
| Integration (WS) | **Phase 4** | pytest-asyncio + TestClient | Full room flows |

### 7.3 `xfail` as spec

The Phase 2 to-do list was encoded as 5 `@pytest.mark.xfail(strict=True)` tests in `tests/domain/`. All 5 were resolved in Phase 2a — the markers are gone and the assertions are now live. Future phases may reintroduce xfail tests to pin upcoming specs; none are open today.

### 7.4 Coverage ratchet

| Phase | `fail_under` | Rationale |
|---|---|---|
| 0 | 0 (permissive baseline) | ✅ shipped |
| 1 | 0 (still permissive) | ✅ shipped at 64% actual |
| 2 | 80 | ✅ shipped at 82% actual (Phase 2b) |
| 3 | 85 | ✅ shipped at 92% actual (Phase 3) |
| 4 | 85 | HTTP + WS handlers excluded via pragma where appropriate |
| 5+ | 90 | Persistence + full stack |

Current coverage: **92%** against `canastra/` (domain + engine + cli).

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
2. **typecheck** — `mypy canastra` (strict on `canastra.domain.*`)
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
- **CLI I/O is routed through injected `input_fn`/`output_fn` callables.** Never call `input()` or `print()` directly from new code in `canastra.cli`; pass the callables through so tests can script input lists without monkeypatching stdin/stdout.
- **`GameState` is a frozen pydantic model.** Mutate via `state.model_copy(update={...})` — direct attribute assignment will raise.
- **`CANASTRA_SEED` env var overrides the random seed** in `canastra.cli.setup.build_config_interactive`. Handy for reproducing a deal during manual testing; leave unset for production runs.

---

## 10. Phase Status

| Phase | Scope | Status | Exit criterion |
|---|---|---|---|
| 0 | Test infra — rename dotted files, add pytest, tests/ dir, smoke test | ✅ 2026-04-17 | `pytest` runs + 10 tests pass |
| 1 | Extract pure domain → `canastra/domain/`, add property tests, xfail Phase 2 specs | ✅ 2026-04-18 | `canastra.domain.*` clean under ruff + mypy strict; 44 pass / 5 xfail |
| 2 | Game engine state machine. Fix the 5 xfails. Implement wild-reinterpret, permanent-dirty, end-of-game scoring algorithm, timer rule, chin semantics | ✅ 2026-04-22 | `(state, action) → (state', events)` for a full game; chin + deck-exhaust + timer scenarios green |
| 3 | Thin CLI adapter over engine (`python -m canastra`); delete legacy flat modules. | ✅ 2026-04-23 | `python -m canastra` plays end-to-end; no module-scope I/O; 196 tests / 92% coverage |
| 4 | FastAPI HTTP + WebSockets. RoomManager, auth (cookie-bound session), private hand broadcasting, reconnect via Snapshot. | ✅ 2026-04-28 | Two browser tabs play a full game over WS on localhost |
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
