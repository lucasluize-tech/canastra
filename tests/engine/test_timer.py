from __future__ import annotations

import random

from canastra.domain.cards import HEARTS, SPADES, Card
from canastra.engine.setup import initial_state
from canastra.engine.state import Meld
from canastra.engine.timer import forced_discard


def test_prefers_duplicate_of_opponent_card(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    opp_meld = [Card(HEARTS, 5), Card(HEARTS, 6), Card(HEARTS, 7)]
    s = s.model_copy(update={
        "hands": {0: [Card(HEARTS, 6), Card(SPADES, "Jack")], 1: [], 2: [], 3: []},
        "melds": {0: [], 1: [Meld(cards=opp_meld)]},
    })
    chosen = forced_discard(s, player_id=0, rng=random.Random(0))
    assert chosen == Card(HEARTS, 6)


def test_never_discards_wild_if_alternative(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = s.model_copy(update={
        "hands": {0: [Card(HEARTS, 2), Card(HEARTS, 5)], 1: [], 2: [], 3: []},
        "melds": {0: [], 1: []},
    })
    chosen = forced_discard(s, player_id=0, rng=random.Random(0))
    assert chosen == Card(HEARTS, 5)


def test_never_discards_ace_if_alternative(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = s.model_copy(update={
        "hands": {0: [Card(HEARTS, "Ace"), Card(HEARTS, 5)], 1: [], 2: [], 3: []},
        "melds": {0: [], 1: []},
    })
    chosen = forced_discard(s, player_id=0, rng=random.Random(0))
    assert chosen == Card(HEARTS, 5)


def test_prefers_permanent_dirty_extend_over_clean_canastra(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    clean_canastra = [Card(HEARTS, r) for r in (3, 4, 5, 6, 7, 8, 9)]
    permanent_dirty_short = [Card(SPADES, "Ace"), Card(SPADES, 2), Card(SPADES, 3)]
    # Both 10H (extends clean canastra) and 4S (extends perm-dirty) are valid;
    # 4S is the lower-harm choice (tier 2 vs tier 6).
    s = s.model_copy(update={
        "hands": {0: [Card(HEARTS, 10), Card(SPADES, 4)], 1: [], 2: [], 3: []},
        "melds": {0: [], 1: [
            Meld(cards=clean_canastra),
            Meld(cards=permanent_dirty_short, permanent_dirty=True),
        ]},
    })
    chosen = forced_discard(s, player_id=0, rng=random.Random(0))
    assert chosen == Card(SPADES, 4)


def test_falls_back_to_wild_if_hand_is_all_wild_and_ace(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = s.model_copy(update={
        "hands": {0: [Card(HEARTS, 2), Card(HEARTS, "Ace")], 1: [], 2: [], 3: []},
        "melds": {0: [], 1: []},
    })
    chosen = forced_discard(s, player_id=0, rng=random.Random(0))
    assert chosen in (Card(HEARTS, 2), Card(HEARTS, "Ace"))
