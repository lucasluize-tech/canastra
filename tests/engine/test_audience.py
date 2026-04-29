"""Audience filtering on engine events."""

import uuid

import pytest

from canastra.engine.events import (
    CardDrawn,
    Chinned,
    DeckReplenished,
    Discarded,
    GameEnded,
    MeldCreated,
    MeldExtended,
    ReserveTaken,
    TrashPickedUp,
    TurnAdvanced,
)

_CARD = {"suit": "♥", "rank": 5}
_MELD_ID = str(uuid.uuid4())


def test_event_base_has_audience_default_none():
    """Every Event subclass should default audience to None (public)."""
    ev = TurnAdvanced(next_player_id=2)
    assert ev.audience is None


@pytest.mark.parametrize(
    "event_cls,kwargs",
    [
        (TurnAdvanced, {"next_player_id": 1}),
        (Discarded, {"player_id": 0, "card": _CARD}),
        (
            MeldCreated,
            {
                "player_id": 0,
                "team_id": 0,
                "meld_id": _MELD_ID,
                "cards": [_CARD],
            },
        ),
        (
            MeldExtended,
            {
                "player_id": 0,
                "team_id": 0,
                "meld_id": _MELD_ID,
                "added": [_CARD],
            },
        ),
        (TrashPickedUp, {"player_id": 0, "cards": [_CARD]}),
        (DeckReplenished, {"team_id": 0, "cards_added": 11}),
        (Chinned, {"team_id": 0}),
        (GameEnded, {"winning_team": 0, "scores": {0: 1000, 1: 500}}),
    ],
)
def test_public_events_default_to_audience_none(event_cls, kwargs):
    ev = event_cls(**kwargs)
    assert ev.audience is None


def test_card_drawn_can_carry_audience():
    ev = CardDrawn(player_id=2, card=_CARD, audience=2)
    assert ev.audience == 2


def test_reserve_taken_can_carry_audience():
    ev = ReserveTaken(player_id=0, team_id=0, reserves_remaining=1, audience=0)
    assert ev.audience == 0


def test_audience_round_trips_through_json():
    ev = CardDrawn(player_id=2, card=_CARD, audience=2)
    blob = ev.model_dump_json()
    restored = CardDrawn.model_validate_json(blob)
    assert restored.audience == 2


# ---------------------------------------------------------------------------
# Handler-level audience annotation tests (Task 2)
# ---------------------------------------------------------------------------

from canastra.domain.cards import HEARTS, Card
from canastra.engine.actions import Discard, Draw
from canastra.engine.engine import apply
from canastra.engine.setup import initial_state
from canastra.engine.state import GameConfig, Phase


def test_handler_sets_audience_on_card_drawn():
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=42)
    state = initial_state(cfg)
    state, events = apply(state, Draw(player_id=state.current_turn.player_id))

    drawn = [ev for ev in events if isinstance(ev, CardDrawn)]
    assert drawn, "Expected at least one CardDrawn event"
    for ev in drawn:
        assert ev.audience == ev.player_id, (
            f"CardDrawn must target the drawing player, got audience={ev.audience}"
        )


def test_handler_sets_audience_on_reserve_taken():
    """Drive game into a state where a player empties their hand and must take a reserve.
    Assert that ReserveTaken events are emitted once per teammate, each with audience=pid."""
    cfg = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, seed=42)
    state = initial_state(cfg)

    # Team 0 has players 0 and 2.  Force player 0's hand to exactly one card,
    # put game in PLAYING phase, so that discarding it triggers reserve pickup.
    only_card = Card(HEARTS, 7)
    state = state.model_copy(
        update={
            "hands": {**state.hands, 0: [only_card]},
            "current_turn": state.current_turn.model_copy(update={"phase": Phase.PLAYING}),
            "phase": Phase.PLAYING,
        }
    )

    _state, events = apply(state, Discard(player_id=0, card=only_card))

    reserve_events = [ev for ev in events if isinstance(ev, ReserveTaken)]

    # team 0 has 2 players → 2 ReserveTaken events
    team_0_players = state.teams[0]
    assert len(reserve_events) == len(team_0_players), (
        f"Expected {len(team_0_players)} ReserveTaken events (one per teammate), "
        f"got {len(reserve_events)}"
    )

    audiences = {ev.audience for ev in reserve_events}
    assert audiences == set(team_0_players), (
        f"Expected audience values {set(team_0_players)}, got {audiences}"
    )

    for ev in reserve_events:
        assert ev.player_id == 0, "player_id on ReserveTaken should be the player who emptied"
        assert ev.team_id == 0
        assert ev.audience is not None, "audience must not be None"


# ---------------------------------------------------------------------------
# Truth-table over every Event subclass — guards against new event types
# being added without an audience-policy decision.
# ---------------------------------------------------------------------------

PUBLIC_EVENT_TYPES = (
    TurnAdvanced,
    Discarded,
    MeldCreated,
    MeldExtended,
    TrashPickedUp,
    DeckReplenished,
    Chinned,
    GameEnded,
)
PRIVATE_EVENT_TYPES = (CardDrawn, ReserveTaken)


def _construct_dummy(event_cls):
    if event_cls is TurnAdvanced:
        return event_cls(next_player_id=1)
    if event_cls is Discarded:
        return event_cls(player_id=0, card=_CARD)
    if event_cls is MeldCreated:
        return event_cls(player_id=0, team_id=0, meld_id=_MELD_ID, cards=[_CARD])
    if event_cls is MeldExtended:
        return event_cls(player_id=0, team_id=0, meld_id=_MELD_ID, added=[_CARD])
    if event_cls is TrashPickedUp:
        return event_cls(player_id=0, cards=[_CARD])
    if event_cls is DeckReplenished:
        return event_cls(team_id=0, cards_added=1)
    if event_cls is Chinned:
        return event_cls(team_id=0)
    if event_cls is GameEnded:
        return event_cls(winning_team=0, scores={0: 1, 1: 0})
    if event_cls is CardDrawn:
        return event_cls(player_id=2, card=_CARD, audience=2)
    if event_cls is ReserveTaken:
        return event_cls(player_id=0, team_id=0, reserves_remaining=1, audience=0)
    raise NotImplementedError(event_cls)


@pytest.mark.parametrize("event_cls", PUBLIC_EVENT_TYPES)
def test_public_event_audience_is_none(event_cls):
    ev = _construct_dummy(event_cls)
    assert ev.audience is None


@pytest.mark.parametrize("event_cls", PRIVATE_EVENT_TYPES)
def test_private_event_audience_is_set_when_provided(event_cls):
    ev = _construct_dummy(event_cls)
    assert ev.audience is not None
