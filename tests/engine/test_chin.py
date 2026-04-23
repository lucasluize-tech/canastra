from __future__ import annotations

from canastra.domain.cards import HEARTS, Card
from canastra.engine.actions import CreateMeld, Discard, Draw
from canastra.engine.engine import apply
from canastra.engine.events import Chinned, GameEnded
from canastra.engine.setup import initial_state
from canastra.engine.state import Phase


def _clean_canastra_cards():
    return [Card(HEARTS, r) for r in (3, 4, 5, 6, 7, 8, 9)]


def test_hand_empty_via_play_pulls_reserve(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    meld = _clean_canastra_cards()
    # Put exactly the meld in hand 0 — playing it empties the hand mid-turn.
    s = s.model_copy(update={"hands": {**s.hands, 0: list(meld)}})
    s, _ = apply(s, Draw(player_id=0))
    # Extra card from draw makes hand length meld+1; play the meld
    # (only 7 cards), hand still has 1 card, so no empty-hand trigger.
    # To really force empty-hand: put the meld + 0 extra.
    s = s.model_copy(update={"hands": {**s.hands, 0: list(meld)}})
    s = s.model_copy(
        update={
            "current_turn": s.current_turn.model_copy(update={"phase": Phase.PLAYING}),
            "phase": Phase.PLAYING,
        }
    )
    before_used = s.reserves_used[0]

    s1, _ = apply(s, CreateMeld(player_id=0, cards=meld))
    assert s1.reserves_used[0] == before_used + 1
    assert len(s1.hands[0]) == 11  # took reserve
    assert s1.current_turn.player_id == 0
    assert s1.current_turn.phase is Phase.PLAYING  # same turn continues


def test_hand_empty_via_discard_pulls_reserve_and_advances(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    only_card = Card(HEARTS, 7)
    s = s.model_copy(
        update={
            "hands": {**s.hands, 0: [only_card]},
            "current_turn": s.current_turn.model_copy(update={"phase": Phase.PLAYING}),
            "phase": Phase.PLAYING,
        }
    )
    before_used = s.reserves_used[0]

    s1, _ = apply(s, Discard(player_id=0, card=only_card))
    assert s1.reserves_used[0] == before_used + 1
    assert len(s1.hands[0]) == 11
    assert s1.current_turn.player_id == 1  # turn advanced


def test_chin_when_reserves_empty_and_clean_canastra(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    meld = _clean_canastra_cards()
    # Force reserves exhausted for team 0
    s = s.model_copy(
        update={
            "reserves": {**s.reserves, 0: []},
            "reserves_used": {**s.reserves_used, 0: 2},
            # Team 0 already has a clean canastra
            "melds": {
                **s.melds,
                0: [__import__("canastra.engine.state", fromlist=["Meld"]).Meld(cards=meld)],
            },
            "hands": {**s.hands, 0: [Card(HEARTS, 10)]},
            "current_turn": s.current_turn.model_copy(update={"phase": Phase.PLAYING}),
            "phase": Phase.PLAYING,
        }
    )

    s1, events = apply(s, Discard(player_id=0, card=Card(HEARTS, 10)))
    assert s1.phase is Phase.ENDED
    assert s1.chin_team == 0
    assert any(isinstance(e, Chinned) for e in events)
    assert any(isinstance(e, GameEnded) for e in events)


def test_game_ends_when_reserves_empty_no_canastra(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = s.model_copy(
        update={
            "reserves": {**s.reserves, 0: []},
            "reserves_used": {**s.reserves_used, 0: 2},
            "hands": {**s.hands, 0: [Card(HEARTS, 10)]},
            "current_turn": s.current_turn.model_copy(update={"phase": Phase.PLAYING}),
            "phase": Phase.PLAYING,
        }
    )
    s1, events = apply(s, Discard(player_id=0, card=Card(HEARTS, 10)))
    assert s1.phase is Phase.ENDED
    assert s1.chin_team is None
    assert any(isinstance(e, GameEnded) for e in events)
