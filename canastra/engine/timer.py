"""Forced discard selection for the optional timer rule.

When the 1-minute timer expires, the engine auto-discards. Priority
ladder (lowest harm first):

1. Discard a card the opponent already has on their table sets.
2. Extends a permanent-dirty opponent set.
3. Extends a short dirty opponent set.
4. Extends a short clean opponent set.
5. Extends an opponent dirty canastra.
6. Extends an opponent clean canastra.

Hard avoid: never pick a wild (rank 2) or an Ace unless no other
option exists.
"""

from __future__ import annotations

import random

from canastra.domain.cards import Card
from canastra.domain.rules import WILD_RANK, extends_set, is_clean
from canastra.engine.state import GameState, Meld

_MIN_CANASTRA = 7


def _is_canastra(m: Meld) -> bool:
    return len(m.cards) >= _MIN_CANASTRA


def _harm_tier(card: Card, opp_melds: list[Meld]) -> int:
    """Lower tier = less harmful to discard. Returns 7 if no interaction."""
    # Tier 1: duplicates opponent card exactly (wasted play for them)
    for m in opp_melds:
        if card in m.cards:
            return 1

    # Tier 2..6: extend various categories
    extendable_tiers: list[int] = []
    for m in opp_melds:
        if not extends_set(list(m.cards), [card]):
            continue
        canastra = _is_canastra(m)
        clean = is_clean(m.cards)
        if m.permanent_dirty:
            extendable_tiers.append(2)
        elif not canastra and not clean:
            extendable_tiers.append(3)
        elif not canastra and clean:
            extendable_tiers.append(4)
        elif canastra and not clean:
            extendable_tiers.append(5)
        else:  # canastra and clean
            extendable_tiers.append(6)

    if extendable_tiers:
        return min(extendable_tiers)
    return 7  # neutral — does not interact


def _opp_team(state: GameState, player_id: int) -> int:
    for tid, members in state.teams.items():
        if player_id not in members:
            return tid
    raise KeyError(player_id)


def forced_discard(
    state: GameState, player_id: int, rng: random.Random | None = None
) -> Card:
    rng = rng or random.Random()
    hand = state.hands[player_id]
    if not hand:
        raise ValueError(f"player {player_id} has no hand to discard from")

    opp_tid = _opp_team(state, player_id)
    opp_melds = state.melds[opp_tid]

    def _is_wild_or_ace(c: Card) -> bool:
        return c.rank == WILD_RANK or c.rank == "Ace"

    preferred = [c for c in hand if not _is_wild_or_ace(c)]
    pool = preferred if preferred else list(hand)

    scored = [(c, _harm_tier(c, opp_melds)) for c in pool]
    best_tier = min(t for _, t in scored)
    candidates = [c for c, t in scored if t == best_tier]
    return rng.choice(candidates)
