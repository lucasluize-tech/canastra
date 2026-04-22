"""Initial state construction.

Builds a fully-seeded GameState from a GameConfig. Deterministic:
same config.seed -> same state (card-for-card).
"""

from __future__ import annotations

import random

from canastra.domain.cards import Deck
from canastra.engine.state import GameConfig, GameState, Phase, TurnState

_HAND_SIZE: int = 11


def initial_state(config: GameConfig) -> GameState:
    rng = random.Random(config.seed)
    deck = Deck(n=config.num_decks)
    rng.shuffle(deck.cards)

    # Deal player hands (11 cards each)
    hands: dict[int, list] = {pid: [] for pid in range(config.num_players)}
    for _ in range(_HAND_SIZE):
        for pid in range(config.num_players):
            hands[pid].append(deck.deal())

    # Deal reserves per team (each reserve hand = 11 cards)
    reserves: dict[int, list[list]] = {0: [], 1: []}
    for _ in range(config.reserves_per_team):
        for team_id in (0, 1):
            reserve_hand = [deck.deal() for _ in range(_HAND_SIZE)]
            reserves[team_id].append(reserve_hand)

    # Assign teams by seat parity
    seat_order = list(range(config.num_players))
    teams = {
        0: [pid for pid in seat_order if pid % 2 == 0],
        1: [pid for pid in seat_order if pid % 2 == 1],
    }

    return GameState(
        config=config,
        seat_order=seat_order,
        teams=teams,
        hands=hands,
        melds={0: [], 1: []},
        reserves=reserves,
        reserves_used={0: 0, 1: 0},
        deck=deck.cards,  # whatever remains
        trash=[],
        current_turn=TurnState(player_id=0, phase=Phase.WAITING_DRAW),
        phase=Phase.WAITING_DRAW,
        action_seq=0,
    )
