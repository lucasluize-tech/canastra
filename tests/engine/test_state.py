from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from canastra.domain.cards import HEARTS, Card
from canastra.engine.state import GameConfig, GameState, Meld, Phase, TurnState


def test_config_defaults_for_4p2d():
    c = GameConfig(num_players=4, num_decks=2, reserves_per_team=2, timer_enabled=False, seed=42)
    assert c.num_players == 4
    assert c.num_decks == 2
    assert c.reserves_per_team == 2
    assert c.timer_enabled is False
    assert c.seed == 42
    assert c.num_teams == 2
    assert c.players_per_team == 2


@pytest.mark.parametrize(
    "n_players,n_decks,reserves",
    [
        (3, 2, 2),  # odd players
        (2, 2, 2),  # below minimum
        (4, 1, 2),  # odd decks
        (4, 2, 1),  # reserves below 2
        (4, 2, 3),  # reserves above num_decks
    ],
)
def test_config_rejects_invalid(n_players, n_decks, reserves):
    with pytest.raises(ValidationError):
        GameConfig(
            num_players=n_players,
            num_decks=n_decks,
            reserves_per_team=reserves,
            timer_enabled=False,
            seed=0,
        )


def test_config_serialization_round_trip():
    c = GameConfig(num_players=6, num_decks=6, reserves_per_team=3, timer_enabled=True, seed=7)
    assert GameConfig.model_validate_json(c.model_dump_json()) == c


def _h(rank):
    return Card(HEARTS, rank)


def test_meld_has_stable_uuid():
    m = Meld(cards=[_h(3), _h(4), _h(5)])
    assert isinstance(m.id, UUID)
    assert m.permanent_dirty is False


def test_meld_two_instances_have_distinct_ids():
    m1 = Meld(cards=[_h(3), _h(4), _h(5)])
    m2 = Meld(cards=[_h(3), _h(4), _h(5)])
    assert m1.id != m2.id


def test_meld_serialization_round_trip():
    m = Meld(cards=[_h(3), _h(4), _h(5)], permanent_dirty=True)
    assert Meld.model_validate_json(m.model_dump_json()) == m


def _config_4p2d():
    return GameConfig(num_players=4, num_decks=2, reserves_per_team=2, timer_enabled=False, seed=1)


def test_phase_values():
    assert {p.value for p in Phase} == {"waiting_draw", "playing", "discarding", "ended"}


def test_gamestate_minimal_construction():
    cfg = _config_4p2d()
    s = GameState(
        config=cfg,
        seat_order=[0, 1, 2, 3],
        teams={0: [0, 2], 1: [1, 3]},
        hands={0: [], 1: [], 2: [], 3: []},
        melds={0: [], 1: []},
        reserves={0: [], 1: []},
        reserves_used={0: 0, 1: 0},
        deck=[],
        trash=[],
        current_turn=TurnState(player_id=0, phase=Phase.WAITING_DRAW),
        phase=Phase.WAITING_DRAW,
        action_seq=0,
    )
    assert s.current_turn.player_id == 0
    assert s.phase is Phase.WAITING_DRAW


def test_gamestate_serialization_round_trip():
    cfg = _config_4p2d()
    s = GameState(
        config=cfg,
        seat_order=[0, 1, 2, 3],
        teams={0: [0, 2], 1: [1, 3]},
        hands={0: [_h(3)], 1: [], 2: [], 3: []},
        melds={0: [], 1: []},
        reserves={0: [], 1: []},
        reserves_used={0: 0, 1: 0},
        deck=[_h(4)],
        trash=[_h(5)],
        current_turn=TurnState(player_id=0, phase=Phase.WAITING_DRAW),
        phase=Phase.WAITING_DRAW,
        action_seq=0,
    )
    blob = s.model_dump_json()
    s2 = GameState.model_validate_json(blob)
    assert s2 == s
