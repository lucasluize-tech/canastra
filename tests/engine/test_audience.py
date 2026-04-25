"""Audience filtering on engine events."""

import uuid

import pytest

from canastra.domain.cards import Card
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
