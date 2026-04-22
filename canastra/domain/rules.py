"""Rule predicates for Canastra sets (runs).

The canonical family variant: a set is a same-suit, monotonic-rank run of at
least 3 cards. Ace can be low (slot 1) or high (slot 14); both Aces may
appear in a single 14-card run. Rank 2 is the wild: a "2" in its own
rank-2 slot whose suit matches the run's suit is a *natural* 2 (does not
consume a wild slot); every other "2" is a wild. A set may contain at
most 2 rank-2 cards total (natural + wild combined).

The core helper is :func:`_min_wild_count`, an existential search over:

* which slots the Aces occupy (A-low = 1, A-high = 14, or both),
* whether a matching-suit 2 is treated as natural at slot 2,

returning the smallest wild count that yields a valid run window
``[start, start + L - 1]`` inside ``[1, 14]``. ``is_in_order`` reports
existence; ``is_clean`` requires an interpretation with zero wilds;
``extends_set`` reuses the helper on the concatenation and additionally
caps total rank-2 cards at 2 (Canastra rule 4.2 in the canonical memo).

Rank 2 is the wild constant.
"""

from __future__ import annotations

from typing import Any

from canastra.domain.cards import Card

WILD_RANK: int = 2
_MIN_RUN: int = 3
_MAX_WILDS: int = 2
_MIN_CANASTRA: int = 7


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


def _min_wild_count(cards: list[Card]) -> int | None:
    """Return the smallest wild count for any valid run interpretation.

    ``None`` means no assignment of Ace positions and natural-2 status
    produces a same-suit, monotonic run fitting inside ranks ``[1, 14]``
    with at most ``_MAX_WILDS`` wild cards.
    """
    length = len(cards)
    if length < _MIN_RUN:
        return None

    non_wild = [c for c in cards if c.rank != WILD_RANK]
    wild_cards = [c for c in cards if c.rank == WILD_RANK]
    if not non_wild:
        return None

    suit = non_wild[0].suit
    if any(c.suit != suit for c in non_wild):
        return None

    ace_count = sum(1 for c in non_wild if c.rank == "Ace")
    if ace_count > 2:
        return None

    other_ranks = [rank_to_number(c.rank) for c in non_wild if c.rank != "Ace"]
    if len(set(other_ranks)) != len(other_ranks):
        return None
    fixed_slots = set(other_ranks)

    if ace_count == 0:
        ace_slot_options: list[set[int]] = [set()]
    elif ace_count == 1:
        ace_slot_options = [{1}, {14}]
    else:
        ace_slot_options = [{1, 14}]

    matching_suit_twos = sum(1 for c in wild_cards if c.suit == suit)
    natural_two_options = [0] if matching_suit_twos == 0 else [0, 1]

    best: int | None = None

    for ace_slots in ace_slot_options:
        for natural_two in natural_two_options:
            wild_count = len(wild_cards) - natural_two
            if wild_count < 0 or wild_count > _MAX_WILDS:
                continue

            slots = fixed_slots | ace_slots
            if natural_two:
                if 2 in slots:
                    continue
                slots = slots | {2}

            if not slots:
                continue
            if len(slots) + wild_count != length:
                continue

            lo, hi = min(slots), max(slots)
            if hi - lo + 1 > length:
                continue

            start_min = max(1, hi - length + 1)
            start_max = min(14 - length + 1, lo)
            if natural_two:
                start_max = min(start_max, 2)
            if start_min > start_max:
                continue

            if best is None or wild_count < best:
                best = wild_count

    return best


def is_in_order(cards: list[Card]) -> bool:
    return _min_wild_count(cards) is not None


def is_clean(cards: list[Card]) -> bool:
    if len(cards) < _MIN_CANASTRA:
        return False
    return _min_wild_count(cards) == 0


def extends_set(chosen_set: list[Card], card_list: list[Card]) -> bool:
    if not chosen_set or not card_list:
        return False
    combined = chosen_set + card_list
    if sum(1 for c in combined if c.rank == WILD_RANK) > _MAX_WILDS:
        return False
    return _min_wild_count(combined) is not None
