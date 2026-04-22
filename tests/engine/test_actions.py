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
    Discarded,
    Event,
    GameEnded,
    MeldCreated,
    MeldExtended,
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
        TurnAdvanced(next_player_id=1),
        Chinned(team_id=0),
        GameEnded(winning_team=0, scores={0: 1100, 1: 200}),
    ]
    for e in events:
        assert e.model_dump_json()
