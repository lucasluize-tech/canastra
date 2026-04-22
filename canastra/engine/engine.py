"""Engine dispatcher.

apply(state, action) -> (state', events)

The engine is a pure function of its inputs: no time, no I/O, no
randomness. Deck-exhaust replenishment from reserves uses a seeded
Random reconstructed from (config.seed, action_seq) so replay stays
deterministic.
"""

from __future__ import annotations

from canastra.engine.actions import (
    Action,
    Chin,
    CreateMeld,
    Discard,
    Draw,
    ExtendMeld,
    PickUpTrash,
)
from canastra.engine.errors import ActionRejected
from canastra.engine.events import CardDrawn, Event, TrashPickedUp
from canastra.engine.state import GameState, Phase, TurnState


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


def _handle_draw(state: GameState, action: Draw) -> tuple[GameState, list[Event]]:
    _require_turn(state, action.player_id)
    _require_phase(state, Phase.WAITING_DRAW)
    if not state.deck:
        raise ActionRejected("deck is empty")

    card = state.deck[-1]
    new_deck = list(state.deck[:-1])
    new_hand = list(state.hands[action.player_id]) + [card]
    new_hands = {**state.hands, action.player_id: new_hand}
    new_turn = TurnState(player_id=action.player_id, phase=Phase.PLAYING)

    new_state = _bump_seq(
        state,
        updates={
            "deck": new_deck,
            "hands": new_hands,
            "current_turn": new_turn,
            "phase": Phase.PLAYING,
        },
    )
    return new_state, [CardDrawn(player_id=action.player_id, card=card)]


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


def apply(state: GameState, action: Action) -> tuple[GameState, list[Event]]:
    if state.phase is Phase.ENDED:
        raise ActionRejected("game has ended")

    if isinstance(action, Draw):
        return _handle_draw(state, action)

    if isinstance(action, PickUpTrash):
        return _handle_pickup_trash(state, action)

    # Other handlers land in later tasks.
    raise ActionRejected(f"action not implemented: {type(action).__name__}")
