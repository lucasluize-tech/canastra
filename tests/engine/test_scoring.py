from __future__ import annotations

from canastra.domain.cards import HEARTS, SPADES, Card
from canastra.engine.scoring import end_of_game_score
from canastra.engine.setup import initial_state
from canastra.engine.state import Meld, Phase


def _clean_canastra(suit=HEARTS):
    return [Card(suit, r) for r in (3, 4, 5, 6, 7, 8, 9)]


def test_no_leftover_scores_canastra_only(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = s.model_copy(
        update={
            "hands": {0: [], 1: [], 2: [], 3: []},
            "melds": {0: [Meld(cards=_clean_canastra())], 1: []},
            "reserves_used": {0: 0, 1: 0},
            "phase": Phase.ENDED,
        }
    )
    result = end_of_game_score(s)
    assert result[0].canastra_bonus == 200
    assert result[0].table_points == 70  # 7 cards * 10
    assert result[0].leftover_debt == 0
    assert result[0].total == 270
    assert result[1].total == 0


def test_leftover_reduces_table_first(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    leftover_card = Card(HEARTS, 10)  # 10pts debt
    short_set = [Card(SPADES, 5), Card(SPADES, 6), Card(SPADES, 7)]  # 30 table pts
    s = s.model_copy(
        update={
            "hands": {0: [leftover_card], 1: [], 2: [], 3: []},
            "melds": {0: [Meld(cards=short_set)], 1: []},
            "phase": Phase.ENDED,
        }
    )
    result = end_of_game_score(s)
    # 10 pts debt absorbed by 10 pts table removal
    # Short set remains at 2 cards (still on table): 20 pts.
    # Actually — our greedy removes from the cheapest set; after removing 1 card
    # from a 3-card set it's now 2 cards = 20 pts, still on table.
    assert result[0].table_points == 20
    assert result[0].canastra_bonus == 0


def test_canastra_trimmed_to_seven_before_sacrifice(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    eight_clean = [Card(HEARTS, r) for r in (3, 4, 5, 6, 7, 8, 9, 10)]
    # Leftover debt = 20pts. Greedy trims to length 7 preserving 200 bonus.
    s = s.model_copy(
        update={
            "hands": {0: [Card(HEARTS, 10), Card(HEARTS, 10)], 1: [], 2: [], 3: []},
            "melds": {0: [Meld(cards=eight_clean)], 1: []},
            "phase": Phase.ENDED,
        }
    )
    result = end_of_game_score(s)
    assert result[0].canastra_bonus == 200
    # Table after trim: 7 cards = 70pts
    assert result[0].table_points == 70


def test_canastra_sacrificed_when_debt_exceeds_available_trim(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    # 1 clean canastra (200 + 70 table) + huge leftover debt
    big_leftover = [Card(HEARTS, 10) for _ in range(20)]  # 200 pts debt
    s = s.model_copy(
        update={
            "hands": {0: big_leftover, 1: [], 2: [], 3: []},
            "melds": {0: [Meld(cards=_clean_canastra())], 1: []},
            "phase": Phase.ENDED,
        }
    )
    result = end_of_game_score(s)
    # Canastra sacrificed → 0 bonus. Table = 0.
    assert result[0].canastra_bonus == 0
    assert result[0].table_points == 0
    # Remaining debt capped at 0
    assert result[0].total == 0


def test_score_floors_at_zero(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    leftover = [Card(HEARTS, 10) for _ in range(100)]
    s = s.model_copy(
        update={
            "hands": {0: leftover, 1: [], 2: [], 3: []},
            "melds": {0: [], 1: []},
            "phase": Phase.ENDED,
        }
    )
    result = end_of_game_score(s)
    assert result[0].total == 0


def test_reserves_and_chin_bonus(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = s.model_copy(
        update={
            "hands": {0: [], 1: [], 2: [], 3: []},
            "melds": {0: [Meld(cards=_clean_canastra())], 1: []},
            "reserves_used": {0: 1, 1: 0},
            "chin_team": 0,
            "phase": Phase.ENDED,
        }
    )
    result = end_of_game_score(s)
    # 200 canastra + 70 table + 100 reserve + 100 chin = 470
    assert result[0].total == 470
