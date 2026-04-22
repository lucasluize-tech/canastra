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
from canastra.domain.rules import extends_set, is_in_order, is_permanent_dirty
from canastra.engine.actions import (
    Action,
    CreateMeld,
    Draw,
    ExtendMeld,
    PickUpTrash,
)
from canastra.engine.errors import ActionRejected
from canastra.engine.events import CardDrawn, Event, MeldCreated, MeldExtended, TrashPickedUp
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
    return new_state, [event]


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
    return new_state, [event]


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

    # Other handlers land in later tasks.
    raise ActionRejected(f"action not implemented: {type(action).__name__}")
