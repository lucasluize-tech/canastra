from __future__ import annotations

from uuid import uuid4

from canastra.domain.cards import Card, HEARTS
from canastra.engine.actions import (
    Action,
    Chin,
    CreateMeld,
    Discard,
    Draw,
    ExtendMeld,
    PickUpTrash,
)
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


def test_all_action_types_serialize():
    actions: list[Action] = [
        Draw(player_id=0),
        PickUpTrash(player_id=0),
        CreateMeld(player_id=0, cards=[Card(HEARTS, 3), Card(HEARTS, 4), Card(HEARTS, 5)]),
        ExtendMeld(player_id=0, meld_id=uuid4(), cards=[Card(HEARTS, 6)]),
        Discard(player_id=0, card=Card(HEARTS, 3)),
        Chin(player_id=0),
    ]
    for a in actions:
        blob = a.model_dump_json()
        a2 = a.__class__.model_validate_json(blob)
        assert a2 == a


def test_all_event_types_construct():
    events: list[Event] = [
        CardDrawn(player_id=0, card=Card(HEARTS, 3)),
        TrashPickedUp(player_id=0, cards=[Card(HEARTS, 3)]),
        MeldCreated(player_id=0, team_id=0, meld_id=uuid4(), cards=[Card(HEARTS, 3)]),
        MeldExtended(player_id=0, team_id=0, meld_id=uuid4(), added=[Card(HEARTS, 6)]),
        Discarded(player_id=0, card=Card(HEARTS, 3)),
        ReserveTaken(player_id=0, team_id=0, reserves_remaining=1),
        DeckReplenished(team_id=0, cards_added=11),
        TurnAdvanced(next_player_id=1),
        Chinned(team_id=0),
        GameEnded(winning_team=0, scores={0: 1100, 1: 200}),
    ]
    for e in events:
        assert e.model_dump_json()


import pytest

from canastra.engine.engine import apply
from canastra.engine.errors import ActionRejected
from canastra.engine.setup import initial_state
from canastra.engine.state import Phase


def test_draw_in_waiting_draw_phase(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    assert len(s.hands[0]) == 11
    top_card = s.deck[-1]

    s1, events = apply(s, Draw(player_id=0))
    assert len(s1.hands[0]) == 12
    assert s1.hands[0][-1] == top_card
    assert len(s1.deck) == len(s.deck) - 1
    assert s1.phase is Phase.PLAYING
    assert s1.current_turn.phase is Phase.PLAYING
    assert s1.action_seq == s.action_seq + 1
    assert len(events) == 1
    assert isinstance(events[0], CardDrawn)
    assert events[0].player_id == 0
    assert events[0].card == top_card


def test_draw_wrong_player_rejected(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    with pytest.raises(ActionRejected, match="not your turn"):
        apply(s, Draw(player_id=1))


def test_draw_wrong_phase_rejected(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s1, _ = apply(s, Draw(player_id=0))
    with pytest.raises(ActionRejected, match="phase"):
        apply(s1, Draw(player_id=0))


def test_pickup_trash_takes_whole_pile(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    trash = [Card(HEARTS, 5), Card(HEARTS, 6), Card(HEARTS, 7)]
    s = s.model_copy(update={"trash": trash})

    s1, events = apply(s, PickUpTrash(player_id=0))
    assert s1.trash == []
    assert len(s1.hands[0]) == 11 + 3
    assert s1.hands[0][-3:] == trash
    assert s1.phase is Phase.PLAYING
    assert len(events) == 1
    assert isinstance(events[0], TrashPickedUp)
    assert events[0].cards == trash


def test_pickup_trash_rejects_empty(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    with pytest.raises(ActionRejected, match="empty"):
        apply(s, PickUpTrash(player_id=0))


def test_pickup_trash_wrong_phase(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = s.model_copy(update={"trash": [Card(HEARTS, 5)]})
    s1, _ = apply(s, PickUpTrash(player_id=0))
    with pytest.raises(ActionRejected, match="phase"):
        apply(s1, PickUpTrash(player_id=0))
