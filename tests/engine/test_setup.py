from __future__ import annotations

from canastra.engine.setup import initial_state
from canastra.engine.state import Phase


def test_initial_state_deals_11_cards_each(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    assert set(s.hands.keys()) == {0, 1, 2, 3}
    for pid in s.hands:
        assert len(s.hands[pid]) == 11
    assert s.trash == []
    assert s.current_turn.player_id == 0
    assert s.phase is Phase.WAITING_DRAW
    assert s.action_seq == 0


def test_initial_state_reserves(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    for team_id in (0, 1):
        assert len(s.reserves[team_id]) == 2
        for reserve_hand in s.reserves[team_id]:
            assert len(reserve_hand) == 11
        assert s.reserves_used[team_id] == 0


def test_initial_state_deck_size(cfg_4p2d):
    # 2 decks = 104 cards. Hands = 4 * 11 = 44. Reserves = 2 teams * 2 * 11 = 44.
    # Deck = 104 - 44 - 44 = 16.
    s = initial_state(cfg_4p2d)
    assert len(s.deck) == 104 - 44 - 44


def test_initial_state_deterministic_by_seed(cfg_4p2d):
    s1 = initial_state(cfg_4p2d)
    s2 = initial_state(cfg_4p2d)
    assert s1 == s2


def test_initial_state_different_seed_differs(cfg_4p2d):
    s1 = initial_state(cfg_4p2d)
    alt = cfg_4p2d.model_copy(update={"seed": cfg_4p2d.seed + 1})
    s2 = initial_state(alt)
    assert s1 != s2


def test_initial_state_team_assignment(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    assert s.teams[0] == [0, 2]
    assert s.teams[1] == [1, 3]
    assert s.seat_order == [0, 1, 2, 3]


def test_initial_state_6p6d_shape(cfg_6p6d):
    s = initial_state(cfg_6p6d)
    # 6 decks = 312. Hands = 6*11 = 66. Reserves = 2 teams * 3 * 11 = 66.
    # Deck = 312 - 66 - 66 = 180.
    assert len(s.deck) == 312 - 66 - 66
    assert s.teams[0] == [0, 2, 4]
    assert s.teams[1] == [1, 3, 5]
