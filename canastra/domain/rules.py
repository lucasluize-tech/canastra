"""Rule predicates for Canastra sets (runs).

Phase 1 port. Logic is the legacy ``helpers.py`` logic — bugs and all —
but with the undefined-``prev`` ``NameError`` in ``extends_set`` fixed so
callers do not crash. Property tests (``tests/domain/test_rules_properties``)
encode the canonical family rules from the memory note
``project_canastra_rules.md``; those tests are the spec the Phase-2 rewrite
must satisfy. Expect several of them to fail against this port — that is
the signal, not a bug in the tests.

Known remaining bugs this port does NOT fix (Phase 2 territory):
  * Wild reinterpretation on extend is not supported.
  * Permanent-dirty sets are not represented.
  * ``is_in_order`` does not correctly handle wild at the first or last
    position, or multiple wilds.
  * ``extends_set`` uses a suit from the last card instead of a set-wide
    suit check.

Rank ``2`` is the wild constant.
"""

from __future__ import annotations

from typing import Any

from canastra.domain.cards import Card

WILD_RANK: int = 2


def rank_to_number(rank: Any, high_ace: bool = False) -> int:
    if rank == "Ace":
        return 14 if high_ace else 1
    if rank == "Jack":
        return 11
    if rank == "Queen":
        return 12
    if rank == "King":
        return 13
    return int(rank)


def is_in_order(cards: list[Card]) -> bool:
    cards = sorted(cards)
    first, last = cards[0], cards[-1]
    high_ace = first.rank == "Ace" and (last.rank == "King" or last.rank == "Queen")

    for i in range(1, len(cards) - 1):
        current_rank = rank_to_number(cards[i].rank, high_ace)
        previous_rank = rank_to_number(cards[i - 1].rank, high_ace)
        next_rank = rank_to_number(cards[i + 1].rank, high_ace)

        if current_rank == 2:
            if high_ace is True and last.rank == "Queen":
                if next_rank != previous_rank - 2:
                    return False
            elif high_ace is True and last.rank == "King":
                if next_rank != previous_rank - 1:
                    return False
            else:
                if next_rank != previous_rank + 2:
                    return False
        elif previous_rank == 2:
            if current_rank + 1 == next_rank or current_rank + 2 == next_rank:
                continue
            return False
        else:
            if previous_rank == 14:
                if current_rank + 1 != next_rank:
                    return False
            elif current_rank != previous_rank + 1 and first.rank != 2:
                return False

    return True


def extends_set(chosen_set: list[Card], card_list: list[Card]) -> bool:
    """Return True iff ``card_list`` can extend ``chosen_set``.

    Phase-1 port of the legacy implementation. Fixes the undefined-``prev``
    ``NameError`` (original code read ``prev`` on the first iteration before
    any assignment); ``prev`` is seeded from the first card here instead.

    Does NOT implement wild reinterpretation — Phase 2. Today this returns
    False for cases the canonical rules would accept.
    """
    num_of_twos = len([card for card in chosen_set if card.rank == WILD_RANK])
    if not chosen_set:
        return False

    prev: int = rank_to_number(chosen_set[0].rank)

    for s in chosen_set:
        suit = chosen_set[-1].suit
        if s.rank == "Ace" and prev == 1:
            continue

        for card in card_list:
            if card.rank == s.rank and card.rank != WILD_RANK:
                return False
            if card.rank == WILD_RANK and card.suit == suit:
                return False
        prev = rank_to_number(s.rank)

    return num_of_twos <= 2


def is_clean(card_list: list[Card]) -> bool:
    if len(card_list) < 7:
        return False

    card_list = sorted(card_list)
    last = card_list[-1]
    num_of_twos = len([card for card in card_list if card.rank == WILD_RANK])
    high_ace = last.rank == "King"

    for i in range(1, len(card_list) - 1):
        cur = rank_to_number(card_list[i].rank, high_ace)
        prev = rank_to_number(card_list[i - 1].rank, high_ace)
        nxt = rank_to_number(card_list[i + 1].rank, high_ace)

        if num_of_twos > 1:
            return False
        if cur == 2 and prev != 1 and nxt != 3:
            return False
        if prev != cur - 1 or nxt != cur + 1:
            if prev == 14:
                continue
            return False

    return True
