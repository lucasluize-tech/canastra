from __future__ import annotations

import pytest

from canastra.engine.actions import Draw
from canastra.engine.engine import apply
from canastra.engine.errors import ActionRejected
from canastra.engine.events import DeckReplenished
from canastra.engine.setup import initial_state


def test_draw_from_empty_deck_replenishes_from_reserve(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    # Force deck empty, leave reserves intact
    s = s.model_copy(update={"deck": []})
    reserves_team0_before = len(s.reserves[0])

    s1, events = apply(s, Draw(player_id=0))
    assert len(s1.hands[0]) == 12
    # Deck went from 0 -> 11 (reserve) -> 10 (after deal)
    assert len(s1.deck) == 10
    # One team lost a reserve
    assert (
        len(s1.reserves[0]) == reserves_team0_before - 1
        or len(s1.reserves[1]) == len(s.reserves[1]) - 1
    )
    assert any(isinstance(e, DeckReplenished) for e in events)


def test_draw_from_empty_deck_no_reserves_ends_game_after_turn(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = s.model_copy(
        update={
            "deck": [],
            "reserves": {0: [], 1: []},
            "reserves_used": {0: 2, 1: 2},
        }
    )
    with pytest.raises(ActionRejected):
        # No cards to draw and no reserves → engine can't produce a card
        apply(s, Draw(player_id=0))


def test_deck_replenish_chooses_team_with_most_reserves_first(cfg_4p2d):
    """Tie-break rule: prefer the team with more reserves (stabilizes behavior)."""
    s = initial_state(cfg_4p2d)
    # Team 0 has 2 reserves, team 1 has 1 reserve
    s = s.model_copy(
        update={
            "deck": [],
            "reserves": {0: s.reserves[0], 1: s.reserves[1][:1]},
        }
    )
    t0_before = len(s.reserves[0])
    t1_before = len(s.reserves[1])

    s1, _ = apply(s, Draw(player_id=0))
    assert len(s1.reserves[0]) == t0_before - 1
    assert len(s1.reserves[1]) == t1_before
