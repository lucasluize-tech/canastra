"""Engine dispatcher.

apply(state, action) -> (state', events)

The engine is a pure function of its inputs: no time, no I/O, no
randomness. Deck-exhaust replenishment from reserves uses a seeded
Random reconstructed from (config.seed, action_seq) so replay stays
deterministic.
"""

from __future__ import annotations

from uuid import UUID

from canastra.domain.cards import Card
from canastra.domain.rules import extends_set, is_clean, is_in_order, is_permanent_dirty
from canastra.engine.actions import (
    Action,
    CreateMeld,
    Discard,
    Draw,
    ExtendMeld,
    PickUpTrash,
)
from canastra.engine.errors import ActionRejected
from canastra.engine.events import (
    CardDrawn,
    Chinned,
    DeckReplenished,
    Discarded,
    Event,
    GameEnded,
    MeldCreated,
    MeldExtended,
    ReserveTaken,
    TrashPickedUp,
    TurnAdvanced,
)
from canastra.engine.state import GameState, Meld, Phase, TurnState


def _bump_seq(state: GameState, *, updates: dict) -> GameState:
    return state.model_copy(update={"action_seq": state.action_seq + 1, **updates})


def _require_turn(state: GameState, player_id: int) -> None:
    if state.current_turn.player_id != player_id:
        raise ActionRejected(
            f"not your turn: expected {state.current_turn.player_id}, got {player_id}"
        )


def _require_phase(state: GameState, *allowed: Phase) -> None:
    if state.current_turn.phase not in allowed:
        raise ActionRejected(
            f"wrong phase: expected {[p.value for p in allowed]}, got {state.current_turn.phase.value}"
        )


def _team_of(state: GameState, player_id: int) -> int:
    for team_id, members in state.teams.items():
        if player_id in members:
            return team_id
    raise ActionRejected(f"unknown player {player_id}")


def _remove_cards_from_hand(hand: list[Card], cards: list[Card]) -> list[Card] | None:
    """Return a new hand with the given cards removed (first-match each),
    or None if any card isn't present.
    """
    remaining = list(hand)
    for c in cards:
        try:
            remaining.remove(c)
        except ValueError:
            return None
    return remaining


def _find_meld(state: GameState, team_id: int, meld_id: UUID) -> int | None:
    for idx, m in enumerate(state.melds[team_id]):
        if m.id == meld_id:
            return idx
    return None


def _team_has_clean_canastra(state: GameState, team_id: int) -> bool:
    return any(is_clean(m.cards) for m in state.melds[team_id])


def _try_empty_hand_resolve(
    state: GameState,
    player_id: int,
    events: list[Event],
    *,
    continue_turn: bool,
) -> tuple[GameState, list[Event]]:
    """If the player's hand is empty, take a reserve or end the game.

    continue_turn=True: empty-by-play branch, keep same turn/phase=PLAYING.
    continue_turn=False: empty-by-discard branch, caller has already
                         advanced the turn; we only swap in the reserve.
    """
    if state.hands[player_id]:
        return state, events

    team_id = _team_of(state, player_id)
    reserves = state.reserves[team_id]
    if reserves:
        new_hand = list(reserves[-1])
        new_reserves = {**state.reserves, team_id: reserves[:-1]}
        new_used = {**state.reserves_used, team_id: state.reserves_used[team_id] + 1}
        new_hands = {**state.hands, player_id: new_hand}
        updates: dict = {"hands": new_hands, "reserves": new_reserves, "reserves_used": new_used}
        if continue_turn:
            updates["current_turn"] = TurnState(player_id=player_id, phase=Phase.PLAYING)
            updates["phase"] = Phase.PLAYING
        new_state = state.model_copy(update=updates)
        events.append(
            ReserveTaken(
                player_id=player_id,
                team_id=team_id,
                reserves_remaining=len(new_reserves[team_id]),
            )
        )
        return new_state, events

    # No reserves left — end game
    chin = _team_has_clean_canastra(state, team_id)
    ended = state.model_copy(
        update={
            "phase": Phase.ENDED,
            "chin_team": team_id if chin else None,
        }
    )
    if chin:
        events.append(Chinned(team_id=team_id))
    # Scoring is computed here once the scoring module lands; for now emit
    # a placeholder GameEnded with empty scores — overwritten by Task 15.
    events.append(GameEnded(winning_team=None, scores={0: 0, 1: 0}))
    return ended, events


def _replenish_deck(state: GameState) -> tuple[GameState, list[Event]]:
    """Move one reserve hand into the deck. Prefer team with more reserves.

    Returns a new state with the reserve promoted or the same state
    unchanged if no reserves exist anywhere.
    """
    candidates = sorted(
        [t for t in (0, 1) if state.reserves[t]],
        key=lambda t: -len(state.reserves[t]),
    )
    if not candidates:
        return state, []
    team_id = candidates[0]
    reserve_cards = list(state.reserves[team_id][-1])
    new_reserves = {**state.reserves, team_id: state.reserves[team_id][:-1]}
    # Promoted reserve becomes the deck (bottom append so next pop is top)
    new_deck = list(state.deck) + reserve_cards
    new_state = state.model_copy(update={"deck": new_deck, "reserves": new_reserves})
    return new_state, [DeckReplenished(team_id=team_id, cards_added=len(reserve_cards))]


def _handle_draw(state: GameState, action: Draw) -> tuple[GameState, list[Event]]:
    _require_turn(state, action.player_id)
    _require_phase(state, Phase.WAITING_DRAW)

    events: list[Event] = []
    working_state = state
    if not working_state.deck:
        working_state, repl_events = _replenish_deck(working_state)
        events.extend(repl_events)
        if not working_state.deck:
            raise ActionRejected("deck and reserves are empty — game cannot continue")

    card = working_state.deck[-1]
    new_deck = list(working_state.deck[:-1])
    new_hand = list(working_state.hands[action.player_id]) + [card]
    new_hands = {**working_state.hands, action.player_id: new_hand}
    new_turn = TurnState(player_id=action.player_id, phase=Phase.PLAYING)

    new_state = _bump_seq(
        working_state,
        updates={
            "deck": new_deck,
            "hands": new_hands,
            "current_turn": new_turn,
            "phase": Phase.PLAYING,
        },
    )
    events.append(CardDrawn(player_id=action.player_id, card=card))
    return new_state, events


def _handle_pickup_trash(state: GameState, action: PickUpTrash) -> tuple[GameState, list[Event]]:
    _require_turn(state, action.player_id)
    _require_phase(state, Phase.WAITING_DRAW)
    if not state.trash:
        raise ActionRejected("trash pile is empty")

    picked = list(state.trash)
    new_hand = list(state.hands[action.player_id]) + picked
    new_hands = {**state.hands, action.player_id: new_hand}
    new_turn = TurnState(player_id=action.player_id, phase=Phase.PLAYING)

    new_state = _bump_seq(
        state,
        updates={
            "trash": [],
            "hands": new_hands,
            "current_turn": new_turn,
            "phase": Phase.PLAYING,
        },
    )
    return new_state, [TrashPickedUp(player_id=action.player_id, cards=picked)]


def _handle_create_meld(state: GameState, action: CreateMeld) -> tuple[GameState, list[Event]]:
    _require_turn(state, action.player_id)
    _require_phase(state, Phase.PLAYING)
    if not is_in_order(action.cards):
        raise ActionRejected("cards do not form a valid run")

    new_hand = _remove_cards_from_hand(state.hands[action.player_id], action.cards)
    if new_hand is None:
        raise ActionRejected("cards not in hand")

    team_id = _team_of(state, action.player_id)
    meld = Meld(
        cards=list(action.cards),
        permanent_dirty=is_permanent_dirty(action.cards),
    )
    new_melds = {**state.melds, team_id: list(state.melds[team_id]) + [meld]}
    new_hands = {**state.hands, action.player_id: new_hand}

    new_state = _bump_seq(state, updates={"melds": new_melds, "hands": new_hands})
    event = MeldCreated(
        player_id=action.player_id,
        team_id=team_id,
        meld_id=meld.id,
        cards=list(action.cards),
    )
    new_state, events_out = _try_empty_hand_resolve(
        new_state, action.player_id, [event], continue_turn=True
    )
    return new_state, events_out


def _handle_extend_meld(state: GameState, action: ExtendMeld) -> tuple[GameState, list[Event]]:
    _require_turn(state, action.player_id)
    _require_phase(state, Phase.PLAYING)
    team_id = _team_of(state, action.player_id)
    idx = _find_meld(state, team_id, action.meld_id)
    if idx is None:
        raise ActionRejected(f"meld {action.meld_id} not found for team {team_id}")

    meld = state.melds[team_id][idx]
    if not extends_set(list(meld.cards), list(action.cards)):
        raise ActionRejected("cards do not extend the meld into a valid run")

    new_hand = _remove_cards_from_hand(state.hands[action.player_id], action.cards)
    if new_hand is None:
        raise ActionRejected("cards not in hand")

    new_cards = list(meld.cards) + list(action.cards)
    new_meld = Meld(
        id=meld.id,
        cards=new_cards,
        permanent_dirty=meld.permanent_dirty or is_permanent_dirty(new_cards),
    )
    new_team_melds = list(state.melds[team_id])
    new_team_melds[idx] = new_meld
    new_melds = {**state.melds, team_id: new_team_melds}
    new_hands = {**state.hands, action.player_id: new_hand}

    new_state = _bump_seq(state, updates={"melds": new_melds, "hands": new_hands})
    event = MeldExtended(
        player_id=action.player_id,
        team_id=team_id,
        meld_id=meld.id,
        added=list(action.cards),
    )
    new_state, events_out = _try_empty_hand_resolve(
        new_state, action.player_id, [event], continue_turn=True
    )
    return new_state, events_out


def _next_player(state: GameState) -> int:
    current = state.current_turn.player_id
    idx = state.seat_order.index(current)
    return state.seat_order[(idx + 1) % len(state.seat_order)]


def _handle_discard(state: GameState, action: Discard) -> tuple[GameState, list[Event]]:
    _require_turn(state, action.player_id)
    _require_phase(state, Phase.PLAYING)
    new_hand = _remove_cards_from_hand(state.hands[action.player_id], [action.card])
    if new_hand is None:
        raise ActionRejected("card not in hand")

    # NOTE: chin-on-discard and reserve-pickup are layered in later tasks.
    new_hands = {**state.hands, action.player_id: new_hand}
    next_pid = _next_player(state)
    new_turn = TurnState(player_id=next_pid, phase=Phase.WAITING_DRAW)

    new_state = _bump_seq(
        state,
        updates={
            "hands": new_hands,
            "trash": list(state.trash) + [action.card],
            "current_turn": new_turn,
            "phase": Phase.WAITING_DRAW,
        },
    )
    base_events: list[Event] = [
        Discarded(player_id=action.player_id, card=action.card),
        TurnAdvanced(next_player_id=next_pid),
    ]
    new_state, events_out = _try_empty_hand_resolve(
        new_state, action.player_id, base_events, continue_turn=False
    )
    return new_state, events_out


def apply(state: GameState, action: Action) -> tuple[GameState, list[Event]]:
    if state.phase is Phase.ENDED:
        raise ActionRejected("game has ended")

    if isinstance(action, Draw):
        return _handle_draw(state, action)

    if isinstance(action, PickUpTrash):
        return _handle_pickup_trash(state, action)

    if isinstance(action, CreateMeld):
        return _handle_create_meld(state, action)

    if isinstance(action, ExtendMeld):
        return _handle_extend_meld(state, action)

    if isinstance(action, Discard):
        return _handle_discard(state, action)

    # Other handlers land in later tasks.
    raise ActionRejected(f"action not implemented: {type(action).__name__}")
